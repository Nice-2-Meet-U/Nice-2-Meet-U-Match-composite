# """
# Database models for the Nice-2-Meet-U-Match application.
# Uses SQLAlchemy ORM with MySQL backend.

# Note: The Match table does not have a foreign key to Pool, allowing
# matches to reference pools that may be managed by external services.
# """

# from sqlalchemy import (
#     Column,
#     Integer,
#     String,
#     ForeignKey,
#     TIMESTAMP,
#     Float,
#     func,
#     UniqueConstraint,
#     Index,
# )
# from sqlalchemy.dialects.mysql import CHAR
# from sqlalchemy.orm import relationship
# import enum
# from uuid import uuid4
# from frameworks.db.session import Base


# # --- ENUMS ---
# class MatchStatus(str, enum.Enum):
#     """Possible states for a match between two users."""

#     waiting = "waiting"
#     accepted = "accepted"
#     rejected = "rejected"


# class DecisionValue(str, enum.Enum):
#     """Possible decision values for a match."""

#     accept = "accept"
#     reject = "reject"


# # --- TABLES ---
# class Pool(Base):
#     """
#     Represents a location-based group of users.
#     Users in the same pool can be matched with each other.
#     """

#     __tablename__ = "pools"

#     id = Column(
#         CHAR(36),
#         primary_key=True,
#         default=lambda: str(uuid4()),
#         index=True,
#         doc="Unique pool identifier (UUID)",
#     )
#     name = Column(String(255), nullable=False, doc="Name of the pool")
#     location = Column(
#         String(255), nullable=True, index=True, doc="Location/region of the pool"
#     )
#     member_count = Column(
#         Integer, nullable=False, default=0, doc="Number of members in the pool"
#     )
#     created_at = Column(
#         TIMESTAMP, server_default=func.now(), doc="Pool creation timestamp"
#     )

#     # Relationships
#     members = relationship(
#         "PoolMember",
#         back_populates="pool",
#         cascade="all, delete-orphan",
#         doc="Members in this pool",
#     )

#     def __repr__(self):
#         return f"<Pool(id={self.id}, name={self.name}, location={self.location}, members={self.member_count})>"


# class PoolMember(Base):
#     """
#     Links users to pools with optional coordinate data for spatial matching.
#     """

#     __tablename__ = "pool_members"

#     pool_id = Column(
#         CHAR(36),
#         ForeignKey("pools.id", ondelete="CASCADE"),
#         primary_key=True,
#         doc="Pool the member belongs to",
#     )
#     user_id = Column(CHAR(36), primary_key=True, index=True, doc="User identifier")
#     coord_x = Column(Float, nullable=True, doc="X coordinate (latitude)")
#     coord_y = Column(Float, nullable=True, doc="Y coordinate (longitude)")
#     joined_at = Column(
#         TIMESTAMP, server_default=func.now(), doc="When user joined the pool"
#     )

#     # Relationships
#     pool = relationship("Pool", back_populates="members")

#     # Indexes for efficient queries
#     __table_args__ = (Index("idx_pool_member_user", "user_id"),)

#     def __repr__(self):
#         return f"<PoolMember(pool_id={self.pool_id}, user_id={self.user_id})>"


# class Match(Base):
#     """
#     Represents a potential match between two users in a pool.
#     Status is determined by individual user decisions.

#     Note: pool_id does not have a foreign key constraint, allowing
#     matches to reference pools managed by external services.
#     """

#     __tablename__ = "matches"

#     match_id = Column(
#         CHAR(36),
#         primary_key=True,
#         default=lambda: str(uuid4()),
#         index=True,
#         doc="Unique match identifier (UUID)",
#     )
#     pool_id = Column(
#         CHAR(36),
#         nullable=False,
#         index=True,
#         doc="Pool where this match exists (no FK - may be external)",
#     )
#     user1_id = Column(
#         CHAR(36),
#         nullable=False,
#         index=True,
#         doc="First user (normalized: user1_id < user2_id)",
#     )
#     user2_id = Column(
#         CHAR(36),
#         nullable=False,
#         index=True,
#         doc="Second user (normalized: user1_id < user2_id)",
#     )
#     status = Column(
#         String(20),
#         nullable=False,
#         default=MatchStatus.waiting.value,
#         doc="Match status: waiting, accepted, or rejected",
#     )
#     created_at = Column(
#         TIMESTAMP, server_default=func.now(), doc="Match creation timestamp"
#     )
#     updated_at = Column(
#         TIMESTAMP,
#         server_default=func.now(),
#         onupdate=func.now(),
#         doc="Last update timestamp",
#     )

#     # Relationships (only to MatchDecision, which is in the same service)
#     decisions = relationship(
#         "MatchDecision",
#         back_populates="match",
#         cascade="all, delete-orphan",
#         doc="Decisions made on this match",
#     )

#     # Constraints and indexes
#     __table_args__ = (
#         UniqueConstraint("pool_id", "user1_id", "user2_id", name="uq_pool_pair"),
#         Index("idx_match_pool", "pool_id"),
#         Index("idx_match_user1", "user1_id"),
#         Index("idx_match_user2", "user2_id"),
#         Index("idx_match_status", "status"),
#     )

#     def __repr__(self):
#         return f"<Match(match_id={self.match_id}, pool_id={self.pool_id}, users={self.user1_id}↔{self.user2_id}, status={self.status})>"


# class MatchDecision(Base):
#     """
#     Records an individual user's decision (accept/reject) for a match.
#     Two decisions determine the final match status.
#     """

#     __tablename__ = "match_decisions"

#     match_id = Column(
#         CHAR(36),
#         ForeignKey("matches.match_id", ondelete="CASCADE"),
#         primary_key=True,
#         doc="Match being decided on",
#     )
#     user_id = Column(CHAR(36), primary_key=True, doc="User making the decision")
#     decision = Column(String(10), nullable=False, doc="Decision: accept or reject")
#     decided_at = Column(
#         TIMESTAMP, server_default=func.now(), doc="When decision was made"
#     )

#     # Relationships
#     match = relationship("Match", back_populates="decisions")

#     def __repr__(self):
#         return f"<MatchDecision(match_id={self.match_id}, user_id={self.user_id}, decision={self.decision})>"
