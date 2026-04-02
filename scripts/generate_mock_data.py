import datetime
import os
import random
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path so we can import the agentauth package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentauth.core.models import AdminUser, Agent, AuditLog, Base, Integration
from agentauth.core.security import encrypt_secret, get_password_hash

# Configuration
DB_URL = "sqlite:///agentauth.db"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
db = Session()


def generate_mock_data():
    print("Generating mock data...")
    Base.metadata.create_all(bind=engine)

    # 1. Ensure Admin User exists
    if not db.query(AdminUser).filter_by(username="admin").first():
        admin = AdminUser(username="admin", hashed_password=get_password_hash("password"))
        db.add(admin)
        db.commit()
        print("Created default admin user (admin / password)")

    # 2. Ensure we have agents
    agents = db.query(Agent).all()
    if not agents:
        for i in range(3):
            db.add(Agent(name=f"Bot {i+1}"))
        db.commit()
        agents = db.query(Agent).all()

    # 3. Ensure we have integrations
    integrations = ["gemini", "openai", "anthropic", "mock"]
    for name in integrations:
        if not db.query(Integration).filter(Integration.name == name).first():
            db.add(Integration(name=name, provider_key=encrypt_secret("test_key"), is_active=True))
    db.commit()

    # 4. Generate Logs
    # Create some random audit logs
    for _ in range(50):
        target = random.choice(["gemini", "mock", "gmail"])
        status = random.choice([200, 200, 200, 403, 401])

        p_tokens = None
        c_tokens = None
        t_tokens = None

        if target in ["gemini", "mock"]:
            p_tokens = random.randint(100, 500)
            c_tokens = random.randint(50, 300)
            t_tokens = p_tokens + c_tokens

            log = AuditLog(
                agent_id=random.choice([a.id for a in agents]),
                target_service=target,
                request_details="Mock request to " + target,
                response_status=status,
                timestamp=datetime.datetime.utcnow()
                - datetime.timedelta(minutes=random.randint(0, 10000)),
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
                latency_ms=random.randint(100, 2000),
            )
        db.add(log)

    db.commit()
    print("Successfully generated mock logs.")


if __name__ == "__main__":
    generate_mock_data()
    db.close()
