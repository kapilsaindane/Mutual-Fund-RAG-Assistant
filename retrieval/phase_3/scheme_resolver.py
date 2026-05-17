#!/usr/bin/env python3

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SchemeResolver:
    """
    NER-lite scheme resolver using longest substring matching
    Resolves scheme names and aliases from source registry
    """
    
    def __init__(self, source_registry_path: Optional[Path] = None):
        """
        Initialize scheme resolver
        
        Args:
            source_registry_path: Path to source registry JSON file
        """
        if source_registry_path is None:
            # Default path
            self.source_registry_path = Path(__file__).resolve().parents[2] / "docs" / "phases" / "phase-1" / "source-registry.json"
        else:
            self.source_registry_path = source_registry_path
            
        self.schemes = {}
        self.scheme_aliases = {}
        self._load_schemes()
        
    def _load_schemes(self):
        """Load schemes and aliases from source registry"""
        try:
            with open(self.source_registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            for source in registry.get('sources', []):
                scheme_name = source.get('scheme_name', '')
                url = source.get('url', '')
                
                if scheme_name:
                    # Create scheme entry
                    scheme_id = self._create_scheme_id(scheme_name)
                    self.schemes[scheme_id] = {
                        'id': scheme_id,
                        'name': scheme_name,
                        'url': url,
                        'source_type': source.get('source_type', ''),
                        'aliases': []
                    }
                    
                    # Generate aliases
                    aliases = self._generate_aliases(scheme_name)
                    self.schemes[scheme_id]['aliases'] = aliases
                    
                    # Map aliases to scheme_id
                    for alias in aliases:
                        if alias not in self.scheme_aliases:
                            self.scheme_aliases[alias] = []
                        self.scheme_aliases[alias].append(scheme_id)
                        
        except Exception as e:
            print(f"Warning: Failed to load source registry: {e}")
            # Fallback to hardcoded schemes
            self._load_fallback_schemes()
    
    def _load_fallback_schemes(self):
        """Fallback hardcoded schemes for testing"""
        fallback_schemes = [
            {
                'name': 'HDFC Mid-Cap Fund Direct Growth',
                'url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
                'source_type': 'factsheet'
            },
            {
                'name': 'HDFC Equity Fund Direct Growth',
                'url': 'https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth',
                'source_type': 'factsheet'
            },
            {
                'name': 'HDFC Focused Fund Direct Growth',
                'url': 'https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth',
                'source_type': 'factsheet'
            },
            {
                'name': 'HDFC ELSS Tax Saver Fund Direct Plan Growth',
                'url': 'https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth',
                'source_type': 'factsheet'
            },
            {
                'name': 'HDFC Large Cap Fund Direct Growth',
                'url': 'https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth',
                'source_type': 'factsheet'
            }
        ]
        
        for scheme in fallback_schemes:
            scheme_name = scheme['name']
            scheme_id = self._create_scheme_id(scheme_name)
            aliases = self._generate_aliases(scheme_name)
            
            self.schemes[scheme_id] = {
                'id': scheme_id,
                'name': scheme_name,
                'url': scheme['url'],
                'source_type': scheme['source_type'],
                'aliases': aliases
            }
            
            for alias in aliases:
                if alias not in self.scheme_aliases:
                    self.scheme_aliases[alias] = []
                self.scheme_aliases[alias].append(scheme_id)
    
    def _create_scheme_id(self, scheme_name: str) -> str:
        """Create a consistent scheme ID from scheme name"""
        # Convert to lowercase, replace spaces and special chars with hyphens
        scheme_id = re.sub(r'[^a-z0-9]+', '-', scheme_name.lower())
        scheme_id = scheme_id.strip('-')
        return scheme_id
    
    def _generate_aliases(self, scheme_name: str) -> List[str]:
        """Generate aliases for a scheme name"""
        aliases = []
        name_lower = scheme_name.lower()
        
        # Original name (case variations)
        aliases.append(scheme_name)
        aliases.append(name_lower)
        
        # Remove common prefixes/suffixes
        name_variants = [
            name_lower.replace(' direct growth', ''),
            name_lower.replace(' direct plan growth', ''),
            name_lower.replace(' direct', ''),
            name_lower.replace(' growth', ''),
            name_lower.replace(' fund', ''),
            name_lower.replace(' hdfc ', ' '),
            name_lower.replace('hdfc ', ''),
        ]
        
        for variant in name_variants:
            variant = variant.strip()
            if variant and variant != name_lower:
                aliases.append(variant)
        
        # Extract key terms
        key_terms = []
        if 'mid cap' in name_lower:
            key_terms.extend(['mid cap', 'midcap', 'mid-cap'])
        if 'large cap' in name_lower:
            key_terms.extend(['large cap', 'largecap', 'large-cap'])
        if 'equity' in name_lower:
            key_terms.append('equity')
        if 'focused' in name_lower:
            key_terms.append('focused')
        if 'elss' in name_lower:
            key_terms.extend(['elss', 'tax saver'])
        if 'tax saver' in name_lower:
            key_terms.extend(['tax saver', 'elss'])
        
        aliases.extend(key_terms)
        
        # Remove duplicates and empty strings
        aliases = list(set(alias.strip() for alias in aliases if alias.strip()))
        
        return aliases
    
    def resolve_scheme(self, query: str) -> Optional[Dict]:
        """
        Resolve scheme from query using longest substring matching
        
        Args:
            query: Normalized query string
            
        Returns:
            Scheme dictionary if found, None otherwise
        """
        if not query:
            return None
        
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        # Check all aliases for matches
        for alias, scheme_ids in self.scheme_aliases.items():
            if alias in query_lower:
                # Calculate match score based on length of match
                match_length = len(alias)
                match_score = match_length / len(query_lower)
                
                # Prefer longer matches (longest substring)
                if match_length > best_score:
                    best_score = match_length
                    # Take the first scheme ID for this alias
                    scheme_id = scheme_ids[0]
                    best_match = self.schemes[scheme_id]
        
        return best_match
    
    def resolve_with_confidence(self, query: str) -> Tuple[Optional[Dict], float]:
        """
        Resolve scheme with confidence score
        
        Args:
            query: Normalized query string
            
        Returns:
            Tuple of (scheme_dict, confidence_score)
        """
        if not query:
            return None, 0.0
        
        query_lower = query.lower()
        best_match = None
        best_score = 0
        best_alias = None
        
        # Check all aliases for matches
        for alias, scheme_ids in self.scheme_aliases.items():
            if alias in query_lower:
                # Calculate match score based on length of match
                match_length = len(alias)
                match_score = match_length / len(query_lower)
                
                # Prefer longer matches (longest substring)
                if match_length > best_score:
                    best_score = match_length
                    best_alias = alias
                    scheme_id = scheme_ids[0]
                    best_match = self.schemes[scheme_id]
        
        # Calculate confidence based on match characteristics
        confidence = 0.0
        if best_match:
            # Base confidence from match length
            confidence = min(best_score * 2, 1.0)  # Scale up, cap at 1.0
            
            # Boost confidence for exact scheme name matches
            if best_alias and best_alias == best_match['name'].lower():
                confidence = max(confidence, 0.9)
            
            # Boost confidence for longer aliases (more specific)
            if best_alias and len(best_alias) > 10:
                confidence = min(confidence + 0.1, 1.0)
        
        return best_match, confidence
    
    def get_all_schemes(self) -> List[Dict]:
        """Get all available schemes"""
        return list(self.schemes.values())
    
    def get_scheme_by_id(self, scheme_id: str) -> Optional[Dict]:
        """Get scheme by ID"""
        return self.schemes.get(scheme_id)
    
    def search_schemes(self, query: str, limit: int = 5) -> List[Tuple[Dict, float]]:
        """
        Search for schemes with fuzzy matching
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (scheme_dict, score) tuples
        """
        query_lower = query.lower()
        results = []
        
        for scheme in self.schemes.values():
            score = 0.0
            
            # Check name match
            if query_lower in scheme['name'].lower():
                score = len(query_lower) / len(scheme['name'])
            
            # Check alias matches
            for alias in scheme['aliases']:
                if query_lower in alias.lower():
                    alias_score = len(query_lower) / len(alias)
                    score = max(score, alias_score)
            
            if score > 0:
                results.append((scheme, score))
        
        # Sort by score (descending) and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]


def main():
    """Test scheme resolver"""
    resolver = SchemeResolver()
    
    test_queries = [
        "What is the NAV of HDFC Mid Cap Fund?",
        "ELSS tax saver fund returns",
        "HDFC equity fund direct growth expense ratio",
        "Large cap fund performance",
        "Focused fund lockin period",
        "What about midcap funds?",
        "Tax saving mutual fund",
        "HDFC direct growth scheme",
    ]
    
    print("Scheme Resolver Test:")
    print("=" * 50)
    
    for query in test_queries:
        scheme, confidence = resolver.resolve_with_confidence(query)
        
        print(f"Query: {query}")
        if scheme:
            print(f"Resolved: {scheme['name']}")
            print(f"Confidence: {confidence:.3f}")
            print(f"Scheme ID: {scheme['id']}")
            print(f"Aliases: {scheme['aliases'][:5]}...")  # Show first 5 aliases
        else:
            print("No scheme resolved")
        print("-" * 30)


if __name__ == "__main__":
    main()
