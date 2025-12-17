#!/bin/bash
set -e

PROJECT_ID="cloudexploration-477701"
REGION="us-central1"
SERVICE_NAME="user-matches-service"
INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:matches-db"
TOPIC_NAME="user_left_pool"
FUNCTION_NAME="match-cleanup-handler"
POOLS_SERVICE_URL="https://pools-microservice-870022169527.us-central1.run.app"
MATCHES_SERVICE_URL="https://matches-microservice-870022169527.us-central1.run.app"

# Note: Secrets should be stored in Secret Manager, not hardcoded
# TODO: Replace DB_PASS with Secret Manager reference
DB_USER="gb2975"
DB_PASS="Ciociaobio26@"  # SECURITY WARNING: Move to Secret Manager
DB_NAME="matches"

echo "🚀 Deploying Nice-2-Meet-U-Match Infrastructure..."
# ------------------------------------------------------------------------------
# 2. Build and Deploy Cloud Run Service
# ------------------------------------------------------------------------------
echo "2️⃣ Building container image..."
gcloud builds submit \
  --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest" \
  --project "$PROJECT_ID"

echo ""
echo "3️⃣ Deploying to Cloud Run..."

# Get service URL if it already exists
EXISTING_SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format="value(status.url)" 2>/dev/null || echo "") \


gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME:latest" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,DB_USER=$DB_USER,DB_PASS=$DB_PASS,DB_NAME=$DB_NAME,GCP_PROJECT_ID=$PROJECT_ID,POOL_EVENTS_TOPIC=$TOPIC_NAME,ENABLE_EVENT_PUBLISHING=true,POOLS_SERVICE_URL=$POOLS_SERVICE_URL,MATCHES_SERVICE_URL=$MATCHES_SERVICE_URL" \
  --add-cloudsql-instances "$INSTANCE_CONNECTION_NAME" \
  --timeout=300 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --project "$PROJECT_ID"

# ------------------------------------------------------------------------------
# 3. Get Service Information & Update if needed
# ------------------------------------------------------------------------------
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format="value(status.url)")\

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo "🌐 Service URL: $SERVICE_URL"
echo "📚 API Docs: $SERVICE_URL/docs"
echo ""
echo "📋 Infrastructure Summary:"
echo "   • Cloud Run Service: $SERVICE_NAME"
echo "   • Cloud Function: $FUNCTION_NAME"
echo "   • Pub/Sub Topic: $TOPIC_NAME"
echo "   • Region: $REGION"
echo ""
echo "🔍 Useful Commands:"
echo "   View logs: gcloud run services logs tail $SERVICE_NAME --region=$REGION"
echo "   Function logs: gcloud functions logs read $FUNCTION_NAME --gen2 --region=$REGION --limit=50"
echo "   Test event: gcloud pubsub topics publish $TOPIC_NAME --message='{\"event_type\":\"pool_member_removed\",\"pool_id\":\"test\",\"user_id\":\"test\"}'"
echo ""