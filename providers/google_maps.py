"""Google Maps Places API provider."""

from __future__ import annotations

import googlemaps
from typing import Any, Dict, List, Optional
from core.config import CredentialManager


class GoogleMapsProvider:
    """Google Maps Places API provider."""

    def __init__(self):
        self._client = None

    @property
    def name(self) -> str:
        return "google_maps"

    @property
    def client(self) -> googlemaps.Client:
        if self._client is None:
            api_key = CredentialManager().get_config().google_api_key
            if not api_key:
                raise EnvironmentError("GOOGLE_API_KEY is not set")
            self._client = googlemaps.Client(key=api_key)
        return self._client

    def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        place_type: Optional[str] = None,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for places using Google Maps Places API.

        Args:
            query: Search query (e.g., "coffee shop", "restaurants")
            location: Optional location bias as "lat,lng" or address
            radius: Optional search radius in meters
            place_type: Optional place type filter
            max_results: Maximum number of results to return

        Returns:
            List of place dictionaries with basic info
        """
        params = {"query": query}

        if location:
            params["location"] = location
        if radius:
            params["radius"] = radius
        if place_type:
            params["type"] = place_type

        try:
            places_result = self.client.places(**params)
            places = places_result.get("results", [])[:max_results]

            formatted_results = []
            for place in places:
                formatted_results.append(
                    {
                        "place_id": place.get("place_id"),
                        "name": place.get("name"),
                        "address": place.get("formatted_address"),
                        "rating": place.get("rating"),
                        "user_ratings_total": place.get("user_ratings_total"),
                        "types": place.get("types", []),
                        "location": place.get("geometry", {}).get("location", {}),
                        "business_status": place.get("business_status"),
                    }
                )

            return formatted_results

        except Exception as e:
            raise RuntimeError(f"Google Maps Places search failed: {e}")

    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed information about a place.

        Args:
            place_id: Google Maps Place ID

        Returns:
            Dictionary with detailed place information
        """
        try:
            place_details = self.client.place(
                place_id,
                fields=[
                    "name",
                    "formatted_address",
                    "formatted_phone_number",
                    "website",
                    "rating",
                    "user_ratings_total",
                    "opening_hours",
                    "geometry",
                    "types",
                    "price_level",
                    "photos",
                    "reviews",
                    "business_status",
                ],
            )

            result = place_details.get("result", {})

            # Format photos if present
            photos = result.get("photos", [])
            if photos:
                result["photos"] = [
                    {
                        "photo_reference": photo.get("photo_reference"),
                        "height": photo.get("height"),
                        "width": photo.get("width"),
                        "html_attributions": photo.get("html_attributions", []),
                    }
                    for photo in photos[:5]  # Limit to 5 photos
                ]

            # Format reviews if present
            reviews = result.get("reviews", [])
            if reviews:
                result["reviews"] = [
                    {
                        "author_name": review.get("author_name"),
                        "rating": review.get("rating"),
                        "text": review.get("text"),
                        "time": review.get("time"),
                    }
                    for review in reviews[:5]  # Limit to 5 reviews
                ]

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to get place details: {e}")
