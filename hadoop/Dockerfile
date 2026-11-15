FROM apache/hadoop:3.4.1

USER root
# la imagen es centos 7 sin python, se instala desde vault
RUN sed -i -e 's/mirror.centos.org/vault.centos.org/g' \
           -e 's/^#.*baseurl=http/baseurl=http/g' \
           -e 's/^mirrorlist=http/#mirrorlist=http/g' /etc/yum.repos.d/*.repo \
    && yum install -y python3 \
    && yum clean all
