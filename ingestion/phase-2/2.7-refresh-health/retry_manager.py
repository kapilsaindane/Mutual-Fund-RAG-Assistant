#!/usr/bin/env python3

import json
import smtplib
import subprocess
import sys
import time
from datetime import datetime, timezone
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "state"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "output"
RETRY_STATE_PATH = STATE_DIR / "retry_state.json"
NOTIFICATION_LOG_PATH = OUTPUT_DIR / "notification-log-latest.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class RetryManager:
    def __init__(self, max_retries: int = 3, base_delay: int = 60):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.retry_state = load_json(RETRY_STATE_PATH)
        
    def should_retry(self, operation_id: str, error_type: str = "general") -> bool:
        """Check if operation should be retried"""
        key = f"{operation_id}:{error_type}"
        
        if key not in self.retry_state:
            return True
            
        retry_info = self.retry_state[key]
        return retry_info["attempt_count"] < self.max_retries
    
    def record_attempt(self, operation_id: str, error_type: str = "general", 
                      error_message: str = "") -> None:
        """Record a retry attempt"""
        key = f"{operation_id}:{error_type}"
        
        if key not in self.retry_state:
            self.retry_state[key] = {
                "operation_id": operation_id,
                "error_type": error_type,
                "attempt_count": 0,
                "first_attempt": iso_now(),
                "last_attempt": None,
                "error_messages": []
            }
        
        self.retry_state[key]["attempt_count"] += 1
        self.retry_state[key]["last_attempt"] = iso_now()
        self.retry_state[key]["error_messages"].append({
            "attempt": self.retry_state[key]["attempt_count"],
            "message": error_message,
            "timestamp": iso_now()
        })
        
        save_json(self.retry_state, RETRY_STATE_PATH)
    
    def get_retry_delay(self, operation_id: str, error_type: str = "general") -> int:
        """Calculate exponential backoff delay"""
        key = f"{operation_id}:{error_type}"
        
        if key not in self.retry_state:
            return self.base_delay
            
        attempt = self.retry_state[key]["attempt_count"]
        # Exponential backoff: base_delay * 2^attempt
        return min(self.base_delay * (2 ** attempt), 3600)  # Cap at 1 hour
    
    def reset_retry_state(self, operation_id: str, error_type: str = "general") -> None:
        """Reset retry state for successful operation"""
        key = f"{operation_id}:{error_type}"
        if key in self.retry_state:
            del self.retry_state[key]
            save_json(self.retry_state, RETRY_STATE_PATH)
    
    def run_with_retry(self, operation_id: str, func, *args, **kwargs) -> dict:
        """Run a function with retry logic"""
        error_type = kwargs.pop("error_type", "general")
        
        while self.should_retry(operation_id, error_type):
            try:
                result = func(*args, **kwargs)
                
                # If function returns a dict with status, check it
                if isinstance(result, dict) and result.get("status") == "success":
                    self.reset_retry_state(operation_id, error_type)
                    return result
                elif isinstance(result, dict) and result.get("status") == "failed":
                    error_msg = result.get("error", "Operation failed")
                    self.record_attempt(operation_id, error_type, error_msg)
                    
                    if not self.should_retry(operation_id, error_type):
                        return result
                    
                    delay = self.get_retry_delay(operation_id, error_type)
                    print(f"Retrying {operation_id} in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    # Function doesn't return status dict, assume success
                    self.reset_retry_state(operation_id, error_type)
                    return {"status": "success", "result": result}
                    
            except Exception as e:
                error_msg = str(e)
                self.record_attempt(operation_id, error_type, error_msg)
                
                if not self.should_retry(operation_id, error_type):
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "attempts": self.retry_state[f"{operation_id}:{error_type}"]["attempt_count"]
                    }
                
                delay = self.get_retry_delay(operation_id, error_type)
                print(f"Retrying {operation_id} in {delay} seconds (error: {error_msg})...")
                time.sleep(delay)
        
        return {
            "status": "failed",
            "error": "Max retries exceeded",
            "attempts": self.max_retries
        }


class NotificationManager:
    def __init__(self):
        self.notification_log = load_json(NOTIFICATION_LOG_PATH)
        
    def log_notification(self, notification_type: str, recipient: str, 
                         subject: str, content: str, status: str = "sent") -> None:
        """Log a notification attempt"""
        timestamp = iso_now()
        
        log_entry = {
            "timestamp": timestamp,
            "type": notification_type,
            "recipient": recipient,
            "subject": subject,
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "status": status
        }
        
        if "notifications" not in self.notification_log:
            self.notification_log["notifications"] = []
            
        self.notification_log["notifications"].append(log_entry)
        save_json(self.notification_log, NOTIFICATION_LOG_PATH)
    
    def send_email_notification(self, subject: str, content: str, 
                               recipient: str = None) -> bool:
        """Send email notification (placeholder implementation)"""
        # In a real implementation, you would configure SMTP settings
        # This is a placeholder that logs the notification
        
        recipient = recipient or os.environ.get("ADMIN_EMAIL", "admin@example.com")
        
        try:
            # Placeholder email sending logic
            print(f"EMAIL NOTIFICATION:")
            print(f"To: {recipient}")
            print(f"Subject: {subject}")
            print(f"Content: {content}")
            
            # Log the notification
            self.log_notification("email", recipient, subject, content, "sent")
            return True
            
        except Exception as e:
            print(f"Failed to send email notification: {e}")
            self.log_notification("email", recipient, subject, content, "failed")
            return False
    
    def send_slack_notification(self, message: str, webhook_url: str = None) -> bool:
        """Send Slack notification (placeholder implementation)"""
        webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
        
        if not webhook_url:
            print("Slack webhook URL not configured")
            return False
        
        try:
            # Placeholder Slack sending logic
            print(f"SLACK NOTIFICATION: {message}")
            
            # Log the notification
            self.log_notification("slack", "webhook", "Pipeline Notification", message, "sent")
            return True
            
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
            self.log_notification("slack", "webhook", "Pipeline Notification", message, "failed")
            return False
    
    def notify_pipeline_failure(self, pipeline_report: dict, failed_operations: List[str]) -> None:
        """Send notification for pipeline failure"""
        subject = "❌ Data Refresh Pipeline Failed"
        
        content = f"""
Data refresh pipeline failed at {pipeline_report.get('completed_at', 'Unknown time')}

Failed Operations:
{chr(10).join(f"- {op}" for op in failed_operations)}

Pipeline Summary:
- Total phases: {pipeline_report.get('summary', {}).get('total_phases', 'Unknown')}
- Successful phases: {pipeline_report.get('summary', {}).get('successful_phases', 'Unknown')}
- Failed phases: {pipeline_report.get('summary', {}).get('failed_phases', 'Unknown')}

Please check the pipeline logs and take appropriate action.
        """.strip()
        
        self.send_email_notification(subject, content)
        self.send_slack_notification(f"Data refresh pipeline failed. {len(failed_operations)} operations failed.")
    
    def notify_pipeline_success(self, pipeline_report: dict) -> None:
        """Send notification for pipeline success"""
        subject = "✅ Data Refresh Pipeline Completed Successfully"
        
        content = f"""
Data refresh pipeline completed successfully at {pipeline_report.get('completed_at', 'Unknown time')}

Pipeline Summary:
- Pipeline type: {pipeline_report.get('pipeline_type', 'Unknown')}
- Total phases: {pipeline_report.get('summary', {}).get('total_phases', 'Unknown')}
- URLs processed: {pipeline_report.get('input_summary', {}).get('processed_urls', 'Unknown')}
- Duration: {pipeline_report.get('duration', 'Unknown')}
        """.strip()
        
        self.send_email_notification(subject, content)
        self.send_slack_notification("Data refresh pipeline completed successfully.")


def main():
    """Test the retry and notification mechanisms"""
    import os
    
    # Test retry mechanism
    retry_manager = RetryManager(max_retries=2, base_delay=5)
    
    def failing_function():
        raise Exception("Simulated failure")
    
    def successful_function():
        return {"status": "success", "data": "test data"}
    
    print("Testing retry mechanism with failing function...")
    result = retry_manager.run_with_retry("test_operation", failing_function)
    print(f"Failing function result: {result}")
    
    print("\nTesting retry mechanism with successful function...")
    result = retry_manager.run_with_retry("test_operation_success", successful_function)
    print(f"Successful function result: {result}")
    
    # Test notification mechanism
    notification_manager = NotificationManager()
    
    print("\nTesting notification mechanism...")
    notification_manager.send_email_notification(
        "Test Notification",
        "This is a test notification from the retry manager."
    )
    
    notification_manager.send_slack_notification("Test Slack notification")


if __name__ == "__main__":
    main()
