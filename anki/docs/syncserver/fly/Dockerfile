# Speedrun: minimal image wrapping our fork's prebuilt static musl anki-sync-server.
# The binary is built from THIS fork (anki 26.05b1 + topic_mastery) so its sync
# protocol version matches the desktop and AnkiDroid clients exactly. It is a
# static-pie musl executable, so alpine (musl libc) runs it with zero extra deps.
FROM alpine:3.23

RUN apk add --no-cache ca-certificates && rm -rf /var/cache/apk/*

COPY anki-sync-server /usr/local/bin/anki-sync-server
RUN chmod +x /usr/local/bin/anki-sync-server

# Non-secret config (passwords come from `fly secrets`, see SYNC.md).
# SYNC_BASE points at the mounted volume so user data survives redeploys.
ENV SYNC_HOST=0.0.0.0 \
    SYNC_PORT=8080 \
    SYNC_BASE=/anki_data

EXPOSE 8080

# Built-in healthcheck: exits 0 when the server is up, 1 otherwise, no log spam.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["anki-sync-server", "--healthcheck"]

ENTRYPOINT ["anki-sync-server"]
