# resources/user_match.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from uuid import UUID
import os

from services.user_match_service import (
    get_user_pool_from_service,
    add_user_to_pool_service,
    get_user_matches_from_service,
    generate_matches_for_user_service,
    get_pool_members_from_service,
    get_user_decisions_from_service,
    delete_user_from_pool_service,
    update_user_pool_coordinates_service,
    submit_decision_for_user_match,
)
from models.user_match import (
    UserPoolCreate,
    UserPoolResponse,
    UserPoolRead,
    UserMatchesRead,
    GenerateMatchesResponse,
    UserPoolMembersRead,
    UserDecisionsRead,
    UserPoolDelete,
    UserPoolUpdate,
    UserDecisionCreate,
    UserDecisionResponse,
)

router = APIRouter()

# Get service URL from environment, default to localhost for local testing
POOLS_SERVICE_URL = os.getenv("POOLS_SERVICE_URL", "http://localhost:8000")
MATCHES_SERVICE_URL = os.getenv("MATCHES_SERVICE_URL", "http://localhost:8000")


@router.get("/{user_id}/pool", response_model=UserPoolRead)
def get_user_pool(user_id: UUID):
    """
    Get the pool information for a specific user.
    Returns the pool details and membership information if the user is in a pool.
    """
    try:
        pool_data = get_user_pool_from_service(
            user_id=user_id,
            pools_service_url=POOLS_SERVICE_URL,
        )
        return pool_data

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve user pool: {str(e)}"
        )


@router.post("/{user_id}/pool", response_model=UserPoolResponse, status_code=status.HTTP_201_CREATED)
def add_user_to_pool(user_id: UUID, payload: UserPoolCreate):
    """
    Add a user to a pool by location. Creates a new pool if none exists for the location,
    otherwise adds to a random existing pool at that location.
    """
    try:
        result = add_user_to_pool_service(
            user_id=user_id,
            location=payload.location,
            coord_x=payload.coord_x,
            coord_y=payload.coord_y,
            pools_service_url=POOLS_SERVICE_URL,
            max_pool_size=20,
        )
        return result

    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add user to pool: {str(e)}"
        )


@router.post("/{user_id}/matches", response_model=GenerateMatchesResponse, status_code=status.HTTP_201_CREATED)
def generate_matches_for_user(user_id: UUID):
    """
    Find the user's pool and generate up to 10 random matches with other pool members.
    """
    try:
        result = generate_matches_for_user_service(
            user_id=user_id,
            matches_service_url=MATCHES_SERVICE_URL,
            pools_service_url=POOLS_SERVICE_URL,
            max_matches=10,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate matches: {str(e)}"
        )


@router.get("/{user_id}/matches", response_model=UserMatchesRead)
def get_user_matches(user_id: UUID):
    """
    Get all matches for a specific user.
    Returns a list of matches where the user is a participant.
    """
    try:
        matches = get_user_matches_from_service(
            user_id=user_id,
            matches_service_url=MATCHES_SERVICE_URL,
        )
        return {
            "user_id": user_id,
            "matches_count": len(matches),
            "matches": matches,
        }

    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve user matches: {str(e)}"
        )


@router.get("/{user_id}/pool/members", response_model=UserPoolMembersRead)
def get_user_pool_members(user_id: UUID):
    """
    Get all users in the same pool as the specified user.
    Returns a list of pool members.
    """
    try:
        members = get_pool_members_from_service(
            user_id=user_id,
            pools_service_url=POOLS_SERVICE_URL,
        )
        return {
            "user_id": user_id,
            "members_count": len(members),
            "members": members,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve pool members: {str(e)}"
        )


@router.get("/{user_id}/decisions", response_model=UserDecisionsRead)
def get_user_decisions(user_id: UUID):
    """
    Get all decisions made by a specific user.
    Returns a list of decisions (accept/reject) for matches.
    """
    try:
        decisions = get_user_decisions_from_service(
            user_id=user_id,
            base_url=MATCHES_SERVICE_URL,
        )
        return {
            "user_id": user_id,
            "decisions_count": len(decisions),
            "decisions": decisions,
        }

    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve user decisions: {str(e)}"
        )


@router.delete("/{user_id}/pool", response_model=UserPoolDelete)
def remove_user_from_pool(user_id: UUID):
    """
    Remove a user from their pool.
    This cascades to related matches and decisions through database constraints.
    """
    try:
        result = delete_user_from_pool_service(
            user_id=user_id,
            pools_service_url=POOLS_SERVICE_URL,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to remove user from pool: {str(e)}"
        )


@router.patch("/{user_id}/pool", response_model=UserPoolRead)
def update_user_pool_coordinates(user_id: UUID, payload: UserPoolUpdate):
    """
    Update a user's coordinates in their pool.
    Performs a partial update of the user's location coordinates.
    """
    try:
        result = update_user_pool_coordinates_service(
            user_id=user_id,
            coord_x=payload.coord_x,
            coord_y=payload.coord_y,         
            pools_service_url=POOLS_SERVICE_URL,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update user coordinates: {str(e)}"
        )


@router.post(
    "/{user_id}/matches/{match_id}/decisions",
    response_model=UserDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_user_match_decision(
    user_id: UUID, match_id: UUID, payload: UserDecisionCreate
):
    """
    Submit a decision (accept/reject) for a match on behalf of a user.
    Calls the POST /matches/{match_id}/decisions endpoint.
    """
    try:
        result = submit_decision_for_user_match(
            user_id=user_id,
            match_id=match_id,
            decision=payload.decision,
            matches_service_url=MATCHES_SERVICE_URL,
        )
        return result

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit decision: {str(e)}"
        )
