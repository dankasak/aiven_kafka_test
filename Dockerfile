
FROM fedora:28

## Set correct environment variables.
ENV	HOME=/root \
  LANG=en_US.UTF-8 \
  LC_ALL=en_US.UTF-8

RUN yum install -y python3-pip less postgresql-libs \
  && yum clean all

COPY os_stats_producer.py os_stats_consumer.py requirements.txt kafka_access_key kafka_access_certificate kafka_ca_certificate /

RUN pip3 install --upgrade pip \
  && pip3 install -r /requirements.txt

ENTRYPOINT [ "/usr/bin/python3" ]

#ENTRYPOINT [ "/usr/bin/pudb" ]
