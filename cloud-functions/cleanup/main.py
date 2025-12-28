"""
Cloud Function: Cleanup Orphaned Audio Files
Triggered by Cloud Scheduler to clean up audio files in Storage 
that don't have a corresponding job in Firestore.
"""
import functions_framework
from google.cloud import storage, firestore
import json

# Configuration
BUCKET_NAME = "fognode-audiobooks-1766767722"
FIRESTORE_COLLECTION = "audiobook_jobs"

@functions_framework.http
def cleanup_orphaned_files(request):
    """
    HTTP Cloud Function to clean up orphaned audio files.
    Called by Cloud Scheduler on a schedule.
    """
    try:
        # Initialize clients
        storage_client = storage.Client()
        firestore_client = firestore.Client()
        
        # Get all job IDs from Firestore
        jobs_ref = firestore_client.collection(FIRESTORE_COLLECTION)
        valid_job_ids = set()
        for doc in jobs_ref.stream():
            valid_job_ids.add(doc.id)
        
        # Get all folders in Storage
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix="audiobooks/")
        
        orphaned_files = []
        deleted_count = 0
        
        for blob in blobs:
            # Extract job_id from path: audiobooks/{job_id}/filename.wav
            parts = blob.name.split("/")
            if len(parts) >= 2:
                job_id = parts[1]
                if job_id and job_id not in valid_job_ids:
                    orphaned_files.append(blob.name)
                    blob.delete()
                    deleted_count += 1
        
        result = {
            "status": "success",
            "valid_jobs": len(valid_job_ids),
            "orphaned_files_deleted": deleted_count,
            "deleted_files": orphaned_files[:10]  # Limit response size
        }
        
        print(f"Cleanup completed: {json.dumps(result)}")
        return json.dumps(result), 200, {"Content-Type": "application/json"}
        
    except Exception as e:
        error_result = {"status": "error", "message": str(e)}
        print(f"Cleanup error: {str(e)}")
        return json.dumps(error_result), 500, {"Content-Type": "application/json"}


@functions_framework.cloud_event
def cleanup_on_schedule(cloud_event):
    """
    Cloud Event handler for Pub/Sub trigger from Cloud Scheduler.
    """
    import base64
    
    # Decode message if present
    if cloud_event.data and "message" in cloud_event.data:
        message = cloud_event.data["message"]
        if "data" in message:
            data = base64.b64decode(message["data"]).decode()
            print(f"Received message: {data}")
    
    # Run cleanup
    class FakeRequest:
        pass
    
    result, status, _ = cleanup_orphaned_files(FakeRequest())
    print(f"Scheduled cleanup result: {result}")
    return result

