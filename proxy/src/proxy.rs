#[cfg(test)]
mod tests;

use crate::{
    auth,
    cancellation::{self, CancelMap},
    config::{ProxyConfig, TlsConfig},
    stream::{MeasuredStream, PqStream, Stream},
};
use anyhow::{bail, Context};
use futures::TryFutureExt;
use metrics::{register_int_counter, register_int_counter_vec, IntCounter, IntCounterVec};
use once_cell::sync::Lazy;
use pq_proto::{BeMessage as Be, *};
use std::sync::Arc;
use tokio::io::{AsyncRead, AsyncWrite};
use tracing::{error, info, info_span, Instrument};

const ERR_INSECURE_CONNECTION: &str = "connection is insecure (try using `sslmode=require`)";
const ERR_PROTO_VIOLATION: &str = "protocol violation";

static NUM_CONNECTIONS_ACCEPTED_COUNTER: Lazy<IntCounter> = Lazy::new(|| {
    register_int_counter!(
        "proxy_accepted_connections_total",
        "Number of TCP client connections accepted."
    )
    .unwrap()
});

static NUM_CONNECTIONS_CLOSED_COUNTER: Lazy<IntCounter> = Lazy::new(|| {
    register_int_counter!(
        "proxy_closed_connections_total",
        "Number of TCP client connections closed."
    )
    .unwrap()
});

static NUM_BYTES_PROXIED_COUNTER: Lazy<IntCounterVec> = Lazy::new(|| {
    register_int_counter_vec!(
        "proxy_io_bytes_per_client",
        "Number of bytes sent/received between client and backend.",
        &[
            // Received (rx) / sent (tx).
            "direction",
            // Proxy can keep calling it `project` internally.
            "endpoint_id"
        ]
    )
    .unwrap()
});

/// A small combinator for pluggable error logging.
async fn log_error<R, F>(future: F) -> F::Output
where
    F: std::future::Future<Output = anyhow::Result<R>>,
{
    future.await.map_err(|err| {
        error!("{err}");
        err
    })
}

pub async fn task_main(
    config: &'static ProxyConfig,
    listener: tokio::net::TcpListener,
) -> anyhow::Result<()> {
    scopeguard::defer! {
        info!("proxy has shut down");
    }

    // When set for the server socket, the keepalive setting
    // will be inherited by all accepted client sockets.
    socket2::SockRef::from(&listener).set_keepalive(true)?;

    let cancel_map = Arc::new(CancelMap::default());
    loop {
        let (socket, peer_addr) = listener.accept().await?;
        info!("accepted postgres client connection from {peer_addr}");

        let session_id = uuid::Uuid::new_v4();
        let cancel_map = Arc::clone(&cancel_map);
        tokio::spawn(
            log_error(async move {
                info!("spawned a task for {peer_addr}");

                socket
                    .set_nodelay(true)
                    .context("failed to set socket option")?;

                handle_client(config, &cancel_map, session_id, socket).await
            })
            .instrument(info_span!("client", session = format_args!("{session_id}"))),
        );
    }
}

async fn handle_client(
    config: &ProxyConfig,
    cancel_map: &CancelMap,
    session_id: uuid::Uuid,
    stream: impl AsyncRead + AsyncWrite + Unpin + Send,
) -> anyhow::Result<()> {
    // The `closed` counter will increase when this future is destroyed.
    NUM_CONNECTIONS_ACCEPTED_COUNTER.inc();
    scopeguard::defer! {
        NUM_CONNECTIONS_CLOSED_COUNTER.inc();
    }

    let tls = config.tls_config.as_ref();
    let do_handshake = handshake(stream, tls, cancel_map).instrument(info_span!("handshake"));
    let (mut stream, params) = match do_handshake.await? {
        Some(x) => x,
        None => return Ok(()), // it's a cancellation request
    };

    // Extract credentials which we're going to use for auth.
    let creds = {
        let sni = stream.get_ref().sni_hostname();
        let common_name = tls.and_then(|tls| tls.common_name.as_deref());
        let result = config
            .auth_backend
            .as_ref()
            .map(|_| auth::ClientCredentials::parse(&params, sni, common_name))
            .transpose();

        async { result }.or_else(|e| stream.throw_error(e)).await?
    };

    let client = Client::new(stream, creds, &params, session_id);
    cancel_map
        .with_session(|session| client.connect_to_db(session))
        .await
}

/// Establish a (most probably, secure) connection with the client.
/// For better testing experience, `stream` can be any object satisfying the traits.
/// It's easier to work with owned `stream` here as we need to upgrade it to TLS;
/// we also take an extra care of propagating only the select handshake errors to client.
async fn handshake<S: AsyncRead + AsyncWrite + Unpin>(
    stream: S,
    mut tls: Option<&TlsConfig>,
    cancel_map: &CancelMap,
) -> anyhow::Result<Option<(PqStream<Stream<S>>, StartupMessageParams)>> {
    // Client may try upgrading to each protocol only once
    let (mut tried_ssl, mut tried_gss) = (false, false);

    let mut stream = PqStream::new(Stream::from_raw(stream));
    loop {
        let msg = stream.read_startup_packet().await?;
        info!("received {msg:?}");

        use FeStartupPacket::*;
        match msg {
            SslRequest => match stream.get_ref() {
                Stream::Raw { .. } if !tried_ssl => {
                    tried_ssl = true;

                    // We can't perform TLS handshake without a config
                    let enc = tls.is_some();
                    stream.write_message(&Be::EncryptionResponse(enc)).await?;
                    if let Some(tls) = tls.take() {
                        // Upgrade raw stream into a secure TLS-backed stream.
                        // NOTE: We've consumed `tls`; this fact will be used later.
                        stream = PqStream::new(
                            stream.into_inner().upgrade(tls.to_server_config()).await?,
                        );
                    }
                }
                _ => bail!(ERR_PROTO_VIOLATION),
            },
            GssEncRequest => match stream.get_ref() {
                Stream::Raw { .. } if !tried_gss => {
                    tried_gss = true;

                    // Currently, we don't support GSSAPI
                    stream.write_message(&Be::EncryptionResponse(false)).await?;
                }
                _ => bail!(ERR_PROTO_VIOLATION),
            },
            StartupMessage { params, .. } => {
                // Check that the config has been consumed during upgrade
                // OR we didn't provide it at all (for dev purposes).
                if tls.is_some() {
                    stream.throw_error_str(ERR_INSECURE_CONNECTION).await?;
                }

                info!(session_type = "normal", "successful handshake");
                break Ok(Some((stream, params)));
            }
            CancelRequest(cancel_key_data) => {
                cancel_map.cancel_session(cancel_key_data).await?;

                info!(session_type = "cancellation", "successful handshake");
                break Ok(None);
            }
        }
    }
}

/// Thin connection context.
struct Client<'a, S> {
    /// The underlying libpq protocol stream.
    stream: PqStream<S>,
    /// Client credentials that we care about.
    creds: auth::BackendType<'a, auth::ClientCredentials<'a>>,
    /// KV-dictionary with PostgreSQL connection params.
    params: &'a StartupMessageParams,
    /// Unique connection ID.
    session_id: uuid::Uuid,
}

impl<'a, S> Client<'a, S> {
    /// Construct a new connection context.
    fn new(
        stream: PqStream<S>,
        creds: auth::BackendType<'a, auth::ClientCredentials<'a>>,
        params: &'a StartupMessageParams,
        session_id: uuid::Uuid,
    ) -> Self {
        Self {
            stream,
            creds,
            params,
            session_id,
        }
    }
}

impl<S: AsyncRead + AsyncWrite + Unpin + Send> Client<'_, S> {
    /// Let the client authenticate and connect to the designated compute node.
    async fn connect_to_db(self, session: cancellation::Session<'_>) -> anyhow::Result<()> {
        let Self {
            mut stream,
            creds,
            params,
            session_id,
        } = self;

        let extra = auth::ConsoleReqExtra {
            session_id, // aka this connection's id
            application_name: params.get("application_name"),
        };

        let auth_result = async {
            // `&mut stream` doesn't let us merge those 2 lines.
            let res = creds.authenticate(&extra, &mut stream).await;
            async { res }.or_else(|e| stream.throw_error(e)).await
        }
        .instrument(info_span!("auth"))
        .await?;

        let node = auth_result.value;
        let (db, cancel_closure) = node
            .config
            .connect(params)
            .or_else(|e| stream.throw_error(e))
            .await?;

        let cancel_key_data = session.enable_query_cancellation(cancel_closure);

        // Report authentication success if we haven't done this already.
        // Note that we do this only (for the most part) after we've connected
        // to a compute (see above) which performs its own authentication.
        if !auth_result.reported_auth_ok {
            stream
                .write_message_noflush(&Be::AuthenticationOk)?
                .write_message_noflush(&BeParameterStatusMessage::encoding())?;
        }

        stream
            .write_message_noflush(&BeMessage::ParameterStatus(
                BeParameterStatusMessage::ServerVersion(&db.version),
            ))?
            .write_message_noflush(&Be::BackendKeyData(cancel_key_data))?
            .write_message(&BeMessage::ReadyForQuery)
            .await?;

        // TODO: add more identifiers.
        let metric_id = node.project;

        let m_sent = NUM_BYTES_PROXIED_COUNTER.with_label_values(&["tx", &metric_id]);
        let mut client = MeasuredStream::new(stream.into_inner(), |cnt| {
            // Number of bytes we sent to the client (outbound).
            m_sent.inc_by(cnt as u64);
        });

        let m_recv = NUM_BYTES_PROXIED_COUNTER.with_label_values(&["rx", &metric_id]);
        let mut db = MeasuredStream::new(db.stream, |cnt| {
            // Number of bytes the client sent to the compute node (inbound).
            m_recv.inc_by(cnt as u64);
        });

        // Starting from here we only proxy the client's traffic.
        info!("performing the proxy pass...");
        let _ = tokio::io::copy_bidirectional(&mut client, &mut db).await?;

        Ok(())
    }
}
