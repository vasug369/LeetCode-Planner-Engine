"""LeetCode GraphQL API client for fetching user progress data."""

import requests
from datetime import datetime
from typing import Optional

from app.config import settings

LEETCODE_GRAPHQL_URL = settings.LEETCODE_GRAPHQL_URL


def _graphql_request(query: str, variables: dict = None) -> dict:
    """Send a GraphQL request to LeetCode API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    response = requests.post(LEETCODE_GRAPHQL_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def get_user_profile(username: str = None) -> Optional[dict]:
    """
    Fetch user's LeetCode profile with submission statistics.
    Returns solve counts by difficulty.
    """
    username = username or settings.LEETCODE_USERNAME
    if not username:
        return None

    query = """
    query getUserProfile($username: String!) {
        matchedUser(username: $username) {
            username
            profile {
                realName
                ranking
            }
            submitStatsGlobal {
                acSubmissionNum {
                    difficulty
                    count
                }
            }
        }
    }
    """

    try:
        data = _graphql_request(query, {"username": username})
        user = data.get("data", {}).get("matchedUser")
        if not user:
            print(f"⚠️  User '{username}' not found on LeetCode")
            return None

        stats = {}
        for entry in user.get("submitStatsGlobal", {}).get("acSubmissionNum", []):
            stats[entry["difficulty"]] = entry["count"]

        return {
            "username": user["username"],
            "ranking": user.get("profile", {}).get("ranking"),
            "solved": stats,
        }
    except Exception as e:
        print(f"❌ Error fetching user profile: {e}")
        return None


def get_recent_submissions(username: str = None, limit: int = 200) -> list[dict]:
    """
    Fetch user's recent accepted submissions.
    Returns list of {title, slug, timestamp, lang}.
    """
    username = username or settings.LEETCODE_USERNAME
    if not username:
        return []

    query = """
    query recentAcSubmissions($username: String!, $limit: Int!) {
        recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            timestamp
            statusDisplay
            lang
        }
    }
    """

    try:
        data = _graphql_request(query, {"username": username, "limit": limit})
        submissions = data.get("data", {}).get("recentAcSubmissionList", [])

        results = []
        for sub in submissions:
            results.append({
                "title": sub["title"],
                "slug": sub["titleSlug"],
                "timestamp": datetime.fromtimestamp(int(sub["timestamp"])),
                "lang": sub.get("lang", "unknown"),
            })

        return results
    except Exception as e:
        print(f"❌ Error fetching submissions: {e}")
        return []


def get_user_solved_problems(username: str = None) -> list[str]:
    """
    Fetch the list of all problem slugs the user has solved.
    Returns list of title slugs.
    """
    username = username or settings.LEETCODE_USERNAME
    if not username:
        return []

    query = """
    query userProblemsSolved($username: String!) {
        matchedUser(username: $username) {
            submitStatsGlobal {
                acSubmissionNum {
                    difficulty
                    count
                    submissions
                }
            }
        }
        recentAcSubmissionList(username: $username, limit: 500) {
            titleSlug
            timestamp
        }
    }
    """

    try:
        data = _graphql_request(query, {"username": username})

        submissions = data.get("data", {}).get("recentAcSubmissionList", [])
        solved_slugs = list(set(sub["titleSlug"] for sub in submissions))

        return solved_slugs
    except Exception as e:
        print(f"❌ Error fetching solved problems: {e}")
        return []


def get_problem_stats(username: str = None) -> dict:
    """
    Get aggregated problem solving stats for a user.
    Returns counts by difficulty and total.
    """
    profile = get_user_profile(username)
    if not profile:
        return {"easy": 0, "medium": 0, "hard": 0, "total": 0}

    solved = profile.get("solved", {})
    return {
        "easy": solved.get("Easy", 0),
        "medium": solved.get("Medium", 0),
        "hard": solved.get("Hard", 0),
        "total": solved.get("All", 0),
        "ranking": profile.get("ranking"),
    }


if __name__ == "__main__":
    username = settings.LEETCODE_USERNAME
    if not username:
        print("⚠️  Set LEETCODE_USERNAME in .env file")
    else:
        print(f"🔍 Fetching data for: {username}")
        profile = get_user_profile(username)
        if profile:
            print(f"   Username: {profile['username']}")
            print(f"   Ranking: {profile['ranking']}")
            print(f"   Solved: {profile['solved']}")

        submissions = get_recent_submissions(username, limit=5)
        print(f"\n📝 Recent {len(submissions)} submissions:")
        for s in submissions:
            print(f"   - {s['title']} ({s['lang']}) at {s['timestamp']}")
