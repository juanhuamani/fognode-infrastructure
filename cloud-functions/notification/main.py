"""
Cloud Function: Job Completion Notification
Triggered by Firestore when a job status changes to 'completed'.
Can send notifications via email, webhook, or log for monitoring.
"""
import functions_framework
from google.cloud import firestore
from google.events.cloud import firestore as firestoredata
import json
from datetime import datetime

@functions_framework.cloud_event
def on_job_completed(cloud_event: functions_framework.CloudEvent):
    """
    Triggered when a Firestore document in audiobook_jobs is updated.
    Checks if status changed to 'completed' and sends notification.
    """
    # Parse the Firestore event
    firestore_payload = firestoredata.DocumentEventData()
    firestore_payload._pb.ParseFromString(cloud_event.data)
    
    # Get the updated document data
    new_value = firestore_payload.value
    old_value = firestore_payload.old_value
    
    # Extract fields
    def get_field_value(doc, field_name):
        if field_name in doc.fields:
            field = doc.fields[field_name]
            if field.string_value:
                return field.string_value
            elif field.integer_value:
                return field.integer_value
        return None
    
    new_status = get_field_value(new_value, "status")
    old_status = get_field_value(old_value, "status") if old_value else None
    filename = get_field_value(new_value, "filename")
    job_id = cloud_event.subject.split("/")[-1] if cloud_event.subject else "unknown"
    
    # Check if status changed to completed
    if new_status == "completed" and old_status != "completed":
        notification = {
            "event": "job_completed",
            "job_id": job_id,
            "filename": filename,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Audiobook '{filename}' has been successfully processed!"
        }
        
        # Log notification (in production, send to email/webhook/push)
        print(f"🎉 NOTIFICATION: {json.dumps(notification)}")
        
        # Here you could add:
        # - Send email via SendGrid/Mailgun
        # - Send push notification via Firebase
        # - Call webhook to external service
        # - Send to Pub/Sub for further processing
        
        return notification
    
    elif new_status == "failed" and old_status != "failed":
        notification = {
            "event": "job_failed",
            "job_id": job_id,
            "filename": filename,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Audiobook '{filename}' processing failed!"
        }
        
        print(f"❌ NOTIFICATION: {json.dumps(notification)}")
        return notification
    
    return {"event": "no_action", "status": new_status}


@functions_framework.http
def get_stats(request):
    """
    HTTP endpoint to get processing statistics.
    """
    try:
        db = firestore.Client()
        jobs_ref = db.collection("audiobook_jobs")
        
        stats = {
            "total_jobs": 0,
            "completed": 0,
            "processing": 0,
            "failed": 0,
            "pending": 0
        }
        
        for doc in jobs_ref.stream():
            data = doc.to_dict()
            stats["total_jobs"] += 1
            status = data.get("status", "unknown")
            if status in stats:
                stats[status] += 1
        
        stats["timestamp"] = datetime.utcnow().isoformat()
        
        return json.dumps(stats), 200, {"Content-Type": "application/json"}
        
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {"Content-Type": "application/json"}

