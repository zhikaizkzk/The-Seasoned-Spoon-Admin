from sqlalchemy.orm import Session
from models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Retrieve a user from the database by email address.
    
    Args:
        db (Session): Database session
        email (str): User email address
        
    Returns:
        User | None: User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()
