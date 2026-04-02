import datetime
import os
import random
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path so we can import the agentauth package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentauth.core.models import Agent, AuditLog, Integration

# Configuration
DB_URL = "sqlite:///agentauth.db"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
db = Session()


def generate_mock_data():
    print("Generating mock data...")

    # 1. Ensure we have agents
    agents = db.query(Agent).all()
    if not agents:
        print("No agents found. Please create an agent via UI first.")
        return

    # 2. Ensure we have integrations
    integrations = ["gemini", "openai", "anthropic", "mock"]
    for name in integrations:
        if not db.query(Integration).filter(Integration.name == name).first():
            db.add(Integration(name=name, is_active=True))
    db.commit()

    # 3. Generate Logs
    now = datetime.datetime.utcnow()
    services = ["gemini", "openai", "anthropic", "mock"]
    statuses = [200, 200, 200, 200, 403, 401, 500]

    for _ in range(150):
        agent = random.choice(agents)
        service = random.choice(services)
        status = random.choice(statuses)

        # Random time in the last 24 hours
        minutes_ago = random.randint(0, 24 * 60)
        timestamp = now - datetime.timedelta(minutes=minutes_ago)

        log = AuditLog(
            agent_id=agent.id,
            target_service=service,
            response_status=status,
            timestamp=timestamp,
            request_details=f"Mock request to {service}",
        )
        db.add(log)

    db.commit()
    print("Successfully generated 150 mock logs.")


if __name__ == "__main__":
    generate_mock_data()
    db.close()
