#!/bin/bash
# Create all required Kafka topics with appropriate partition counts
set -e
KAFKA_HOST=${KAFKA_HOST:-localhost:9092}
echo "📨 Creating Kafka topics on $KAFKA_HOST"

create_topic() {
  local topic=$1; local partitions=${2:-4}; local retention=${3:-604800000}  # 7 days
  kafka-topics.sh --bootstrap-server "$KAFKA_HOST" --create --if-not-exists \
    --topic "$topic" --partitions "$partitions" \
    --config retention.ms="$retention" \
    --config compression.type=lz4
  echo "  ✅ $topic ($partitions partitions)"
}

# Azure topics
create_topic "azure.openai.usage"    8
create_topic "azure.foundry.jobs"    4
create_topic "azure.billing.daily"   2
create_topic "azure.ml.compute"      4
create_topic "azure.cognitive.usage" 4

# OpenStack topics
create_topic "openstack.vllm.usage"       8
create_topic "openstack.nova.gpu"         4
create_topic "openstack.ceilometer.samples" 4

# Unified / processed
create_topic "ai.costs.unified"      8 2592000000  # 30 days retention
create_topic "ai.anomalies"          4
create_topic "ai.recommendations"    2
create_topic "ai.costs.dlq"          2 -1  # Infinite retention for DLQ

echo "✅ All Kafka topics created."
