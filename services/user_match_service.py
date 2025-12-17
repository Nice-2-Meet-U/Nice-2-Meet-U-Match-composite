# services/user_match_service.py
from __future__ import annotations

from uuid import UUID
import requests
import random
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.match import MatchGet

logger = logging.getLogger(__name__)

# Default timeout for all HTTP requests (in seconds)
REQUEST_TIMEOUT = 5


def get_user_pool_from_service(user_id: UUID, pools_service_url: str):
    """
    Query the pools service to get pool information for a user.
    Uses /pools/members?user_id={user_id} to find the user's pool membership,
    then retrieves the pool details.
    Returns pool data or raises an exception.
    """
    try:
        # Step 1: Get the user's pool membership
        members_response = requests.get(
            f"{pools_service_url}/pools/members?user_id={user_id}",
            timeout=REQUEST_TIMEOUT
        )
        members_response.raise_for_status()
        members = members_response.json()
        
        if not members or len(members) == 0:
            raise ValueError("User is not a member of any pool")
        
        user_member = members[0]  # Should only be one membership per user
        pool_id = user_member.get("pool_id")
        
        # Step 2: Fetch pool details
        pool_response = requests.get(
            f"{pools_service_url}/pools/{pool_id}",
            timeout=REQUEST_TIMEOUT
        )
        pool_response.raise_for_status()
        user_pool = pool_response.json()
        
        # Step 3: Return combined pool and member information
        return {
            "pool_id": user_pool["id"],
            "pool_name": user_pool["name"],
            "location": user_pool.get("location"),
            "member_count": user_pool.get("member_count"),
            "joined_at": user_member["joined_at"],
            "user_id": user_member["user_id"],
        }

    except ValueError:
        raise
    except requests.RequestException as e:
        raise RuntimeError(f"Service communication error: {str(e)}")


def add_user_to_pool_service(
    user_id: UUID,
    location: str,
    coord_x: Optional[float],
    coord_y: Optional[float],
    pools_service_url: str,
    max_pool_size: int = 20,
):
    """
    Add a user to a pool by location via the pools service.
    Creates a new pool if none exists or all are full.
    Returns pool and member information.
    """
    try:
        # Find pools at the specified location that are not full
        pools_response = requests.get(
            f"{pools_service_url}/pools/?location={location}",
            timeout=REQUEST_TIMEOUT
        )
        pools_response.raise_for_status()
        pools = pools_response.json()

        # Ensure pools is a list
        if not isinstance(pools, list):
            raise RuntimeError(f"Unexpected response format from pools service: {type(pools)}")

        # Filter out full pools
        pools = [p for p in pools if p.get("member_count", 0) < max_pool_size]

        if not pools or len(pools) == 0:
            # No pools exist for this location, create a new one
            pool_name = f"Pool for {location}"
            pool_response = requests.post(
                f"{pools_service_url}/pools/",
                json={
                    "name": pool_name,
                    "location": location,
                },
                timeout=REQUEST_TIMEOUT
            )
            pool_response.raise_for_status()
            pool = pool_response.json()
            
            # Ensure pool is a dict
            if not isinstance(pool, dict):
                raise RuntimeError(f"Unexpected pool response format: {type(pool)}")
        else:
            # Select a random pool from the available pools at this location
            pool = random.choice(pools)

        # Add the user to the selected/created pool
        member_payload = {"user_id": str(user_id)}
        if coord_x is not None:
            member_payload["coord_x"] = coord_x
        if coord_y is not None:
            member_payload["coord_y"] = coord_y

        member_response = requests.post(
            f'{pools_service_url}/pools/{pool["id"]}/members',
            json=member_payload,
            timeout=REQUEST_TIMEOUT
        )
        member_response.raise_for_status()
        member = member_response.json()

        return {
            "user_id": user_id,
            "pool_id": pool["id"],
            "location": location,
            "member": member,
        }

    except KeyError as e:
        raise RuntimeError(f"Missing expected field in response: {str(e)}")
    except requests.RequestException as e:
        raise RuntimeError(f"Service communication error: {str(e)}")


def get_user_matches_from_service(user_id: UUID, matches_service_url: str):
    """
    Get all matches for a user from the matches service.
    Returns a list of matches where the user is a participant.
    """
    try:
        matches_response = requests.get(
            f"{matches_service_url}/matches/?user_id={user_id}",
            timeout=REQUEST_TIMEOUT,
        )
        matches_response.raise_for_status()
        matches = matches_response.json()

        return matches

    except requests.RequestException as e:
        if hasattr(e, "response") and e.response and e.response.status_code == 404:
            return []  # No matches found
        raise RuntimeError(f"Service communication error: {str(e)}")


def generate_matches_for_user_service(
    user_id: UUID,
    matches_service_url: str,
    pools_service_url: str,
    max_matches: int = 10,
):
    """
    Generate matches for a user by:
    1. Finding the user's pool by searching pool_members
    2. Getting all pool members from that pool
    3. Creating matches with random members via matches service
    Returns information about created matches.
    """
    try:
        # Step 1: Find which pool the user is in
        user_pool_data = get_user_pool_from_service(user_id, pools_service_url)
        pool_id = user_pool_data.get("pool_id")

        if not pool_id:
            raise ValueError(
                "User is not a member of any pool. Add user to a pool first."
            )

        # Step 2: Get all members of that pool
        members_response = requests.get(
            f"{pools_service_url}/pools/{pool_id}/members"
        )
        members_response.raise_for_status()
        pool_members = members_response.json()

        # Filter out the current user
        other_members = [
            member for member in pool_members if member.get("user_id") != str(user_id)
        ]

        if not other_members:
            return {
                "message": "No other users in the pool to match with",
                "pool_id": pool_id,
                "matches_created": 0,
                "matches": [],
            }

        # Select up to max_matches random other members
        selected_members = random.sample(
            other_members, min(max_matches, len(other_members))
        )

        # Create matches via matches service using threading for parallel creation
        created_matches = []
        
        def create_match(member):
            """Helper function to create a single match."""
            try:
                match_response = requests.post(
                    f"{matches_service_url}/matches/",
                    json={
                        "pool_id": str(pool_id),
                        "user1_id": str(user_id),
                        "user2_id": str(member.get("user_id")),
                    },
                    timeout=REQUEST_TIMEOUT
                )
                match_response.raise_for_status()
                return match_response.json()
            except requests.RequestException as e:
                # Skip if match already exists or other error (log but don't fail)
                logger.debug(f"Failed to create match with user {member.get('user_id')}: {e}")
                return None
        
        # Use ThreadPoolExecutor to create matches in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_member = {executor.submit(create_match, member): member for member in selected_members}
            for future in as_completed(future_to_member):
                match = future.result()
                if match:
                    created_matches.append(match)

        # Convert raw dict responses to MatchGet model objects for proper validation
        # Log the type and content for debugging
        logger.info(f"Created matches type: {type(created_matches)}, count: {len(created_matches)}")
        if created_matches:
            logger.info(f"First match type: {type(created_matches[0])}, value: {created_matches[0]}")
        
        validated_matches = []
        for match in created_matches:
            # Check if match is already a list (shouldn't be, but being defensive)
            if isinstance(match, list):
                logger.warning(f"Match is a list, extracting first element: {match}")
                match = match[0] if match else {}
            validated_matches.append(MatchGet(**match))

        return {
            "message": f"Generated {len(validated_matches)} matches for user {user_id}",
            "pool_id": pool_id,
            "matches_created": len(validated_matches),
            "matches": validated_matches,
        }

    except ValueError:
        raise
    except requests.RequestException as e:
        raise RuntimeError(f"Service communication error: {str(e)}")


def get_pool_members_from_service(user_id: UUID, pools_service_url: str):
    """
    Get all members in the same pool as the specified user.
    First finds which pool the user is in, then gets all members of that pool.
    Returns a list of pool members.
    """
    try:
        # Step 1: Find which pool the user is in
        user_pool_data = get_user_pool_from_service(user_id, pools_service_url)
        pool_id = user_pool_data.get("pool_id")
        
        if not pool_id:
            raise ValueError("User is not a member of any pool")
        
        # Step 2: Get all members of that pool
        members_response = requests.get(
            f"{pools_service_url}/pools/{pool_id}/members",
            timeout=REQUEST_TIMEOUT
        )
        members_response.raise_for_status()
        members = members_response.json()

        return members

    except ValueError:
        raise
    except requests.RequestException as e:
        raise RuntimeError(f"Service communication error: {str(e)}")


def get_user_decisions_from_service(user_id: UUID, base_url: str):
    """
    Get all decisions made by a specific user.
    Calls the matches service decisions endpoint with user_id filter.
    Returns a list of decisions.
    """
    try:
        # The matches service endpoint supports filtering by user_id
        # We need to get all matches for this user and their decisions
        # Or we can add a general decisions endpoint
        
        # For now, get all matches for the user first
        matches_response = requests.get(
            f"{base_url}/matches/?user_id={user_id}",
            timeout=REQUEST_TIMEOUT,
        )
        matches_response.raise_for_status()
        matches = matches_response.json()
        
        # Then get decisions for each match where this user participated
        all_decisions = []
        for match in matches:
            match_id = match.get("match_id")
            if match_id:
                try:
                    # Try to get this user's decision for this match
                    decision_response = requests.get(
                        f"{base_url}/matches/{match_id}/decisions/{user_id}",
                        timeout=REQUEST_TIMEOUT
                    )
                    if decision_response.status_code == 200:
                        all_decisions.append(decision_response.json())
                except requests.RequestException:
                    # Decision doesn't exist for this match yet
                    pass
        
        return all_decisions

    except requests.RequestException as e:
        if hasattr(e, "response") and e.response and e.response.status_code == 404:
            return []  # No decisions found
        raise RuntimeError(f"Service communication error: {str(e)}")


def submit_decision_for_user_match(
    user_id: UUID,
    match_id: UUID,
    decision: str,
    matches_service_url: str,
):
    """
    Submit a decision for a match on behalf of a user.
    Calls the POST /matches/{match_id}/decisions endpoint.
    Returns the created decision.
    """
    try:
        decision_response = requests.post(
            f"{matches_service_url}/matches/{match_id}/decisions",
            json={
                "match_id": str(match_id),
                "user_id": str(user_id),
                "decision": decision,
            },
            timeout=REQUEST_TIMEOUT
        )
        decision_response.raise_for_status()
        return decision_response.json()

    except requests.RequestException as e:
        if hasattr(e, "response") and e.response:
            if e.response.status_code == 400:
                raise ValueError(f"Invalid decision data: {e.response.text}")
            elif e.response.status_code == 403:
                raise PermissionError("User is not a participant in this match")
            elif e.response.status_code == 404:
                raise ValueError("Match not found")
        raise RuntimeError(f"Service communication error: {str(e)}")


def delete_user_from_pool_service(user_id: UUID, pools_service_url: str):
    """
    Remove a user from their pool.
    Uses the DELETE /pools/members/{user_id} endpoint which finds and removes
    the user's pool membership without requiring pool_id.
    Publishes a pool_member_removed event for async match cleanup.
    """
    try:
        # Remove the user from their pool using the dedicated endpoint
        delete_response = requests.delete(
            f"{pools_service_url}/pools/members/{user_id}",
            timeout=REQUEST_TIMEOUT
        )
        delete_response.raise_for_status()
        result = delete_response.json()
        
        return result

    except requests.RequestException as e:
        if hasattr(e, "response") and e.response and e.response.status_code == 404:
            raise ValueError("User is not a member of any pool")
        raise RuntimeError(f"Service communication error: {str(e)}")


def update_user_pool_coordinates_service(
    user_id: UUID,
    coord_x: Optional[float],
    coord_y: Optional[float],
    pools_service_url: str,
):
    """
    Update a user's coordinates in their pool.
    First finds which pool the user is in, then updates their member record.
    """
    try:
        # Step 1: Find which pool the user is in
        user_pool_data = get_user_pool_from_service(user_id, pools_service_url)
        pool_id = user_pool_data.get("pool_id")
        
        if not pool_id:
            raise ValueError("User is not a member of any pool")
        
        # Step 2: Update the pool member coordinates
        payload = {}
        if coord_x is not None:
            payload["coord_x"] = coord_x
        if coord_y is not None:
            payload["coord_y"] = coord_y
        
        update_response = requests.patch(
            f"{pools_service_url}/pools/{pool_id}/members/{user_id}",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        update_response.raise_for_status()
        member = update_response.json()
        
        # Step 3: Return updated pool info
        return {
            "pool_id": pool_id,
            "pool_name": user_pool_data.get("pool_name"),
            "location": user_pool_data.get("location"),
            "member_count": user_pool_data.get("member_count"),
            "joined_at": member.get("joined_at"),
            "user_id": str(user_id),
        }

    except ValueError:
        raise
    except requests.RequestException as e:
        if hasattr(e, "response") and e.response:
            if e.response.status_code == 404:
                raise ValueError("User is not a member of any pool")
        raise RuntimeError(f"Service communication error: {str(e)}")
