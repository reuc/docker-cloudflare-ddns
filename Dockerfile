FROM reuc/docker-ubuntu

ENV CLOUDFLARE_EMAIL="username" \
    CLOUDFLARE_APIKEY="password" \
    CLOUDFLARE_DELAY="60" \
    CLOUDFLARE_INTERVAL="60" \
    CLOUDFLARE_TRIES="2" \
    CLOUDFLARE_NAME="www" \
    CLOUDFLARE_ZONE="example.com" \
    CLOUDFLARE_RECORDTYPE='A' \
    CLOUDFLARE_RECORDTTL='1' \
    CLOUDFLARE_IPV4=""
    CLOUDFLARE_ID="DomainZoneID"

RUN set -ex; \
    pip install \
        pytz \
        requests --break-system-packages

COPY assets/ /

CMD [ "python3", "-u", "/usr/local/bin/dnsomatic.py" ]

### METADATA ###################################################################

ARG IMAGE
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF
ARG VCS_URL
LABEL \
    org.label-schema.name=$IMAGE \
    org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.version=$VERSION \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.vcs-url=$VCS_URL \
    org.label-schema.schema-version="1.0"