"""
AI Prompt Engineer Agent - Offline Knowledge Base & Adaptive Learning System
Military-grade knowledge management for zero-connectivity environments with continuous learning
"""

import sqlite3
import json
import hashlib
import zlib
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import pickle
import struct
import mmap
import os
from collections import defaultdict
import heapq
import asyncio
from pathlib import Path


class KnowledgeDomain(Enum):
    """Specialized knowledge domains for different operational contexts"""
    MILITARY = "military"
    TECHNICAL = "technical"
    MEDICAL = "medical"
    INTELLIGENCE = "intelligence"
    LOGISTICS = "logistics"
    COMMUNICATIONS = "communications"
    CYBERSECURITY = "cybersecurity"
    ENGINEERING = "engineering"
    GENERAL = "general"


class StorageTier(Enum):
    """Storage tiers for different device capabilities"""
    ULTRA_COMPACT = "ultra_compact"  # <1GB - phones, IoT
    COMPACT = "compact"              # 1-5GB - tablets
    STANDARD = "standard"            # 5-20GB - laptops
    EXTENDED = "extended"            # 20-100GB - workstations


@dataclass
class KnowledgeNode:
    """Individual knowledge unit with compression and relevance tracking"""
    id: str
    domain: KnowledgeDomain
    content: str
    compressed_content: bytes
    embeddings: np.ndarray
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    relevance_score: float = 1.0
    security_classification: str = "UNCLASSIFIED"
    version: int = 1
    dependencies: List[str] = field(default_factory=list)
    
    def compress(self) -> bytes:
        """Compress content for storage efficiency"""
        return zlib.compress(self.content.encode('utf-8'), level=9)
    
    def decompress(self) -> str:
        """Decompress content for use"""
        return zlib.decompress(self.compressed_content).decode('utf-8')
    
    def update_access(self):
        """Update access patterns for adaptive caching"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        # Boost relevance based on usage
        self.relevance_score = min(2.0, self.relevance_score * 1.01)


@dataclass
class LearningEvent:
    """Captures learning from user interactions"""
    timestamp: datetime
    query: str
    enhanced_query: str
    user_feedback: Optional[float]  # -1 to 1 scale
    context: Dict[str, Any]
    outcome: str
    domain: KnowledgeDomain
    
    def to_knowledge_update(self) -> Dict[str, Any]:
        """Convert learning event to knowledge base update"""
        return {
            "pattern": self._extract_pattern(),
            "enhancement": self._extract_enhancement(),
            "context_factors": self._extract_context_factors(),
            "quality_score": self.user_feedback or 0.0
        }
    
    def _extract_pattern(self) -> str:
        """Extract reusable pattern from query"""
        # Simplified pattern extraction
        words = self.query.lower().split()
        return " ".join(words[:5])  # First 5 words as pattern
    
    def _extract_enhancement(self) -> str:
        """Extract enhancement technique used"""
        return self.enhanced_query[:100]  # Simplified
    
    def _extract_context_factors(self) -> List[str]:
        """Extract relevant context factors"""
        return list(self.context.keys())


class OfflineKnowledgeBase:
    """
    Core offline knowledge base with adaptive learning and extreme compression
    Designed for military field operations with zero connectivity
    """
    
    def __init__(self, storage_path: str, storage_tier: StorageTier = StorageTier.STANDARD):
        self.storage_path = Path(storage_path)
        self.storage_tier = storage_tier
        self.db_path = self.storage_path / "knowledge.db"
        self.index_path = self.storage_path / "knowledge.idx"
        self.embeddings_path = self.storage_path / "embeddings.bin"
        
        # Initialize storage
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
        
        # Memory-mapped files for fast access
        self.embeddings_mmap = None
        self.index_cache = {}
        
        # Adaptive learning components
        self.learning_buffer = []
        self.pattern_cache = defaultdict(list)
        self.enhancement_strategies = self._load_enhancement_strategies()
        
        # Domain-specific indexes
        self.domain_indexes = defaultdict(set)
        
        # Storage limits based on tier
        self.storage_limits = {
            StorageTier.ULTRA_COMPACT: 1 * 1024**3,     # 1GB
            StorageTier.COMPACT: 5 * 1024**3,           # 5GB
            StorageTier.STANDARD: 20 * 1024**3,         # 20GB
            StorageTier.EXTENDED: 100 * 1024**3         # 100GB
        }
        
    def _initialize_database(self):
        """Initialize SQLite database for knowledge storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    id TEXT PRIMARY KEY,
                    domain TEXT,
                    content_hash TEXT,
                    compressed_content BLOB,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    relevance_score REAL DEFAULT 1.0,
                    security_classification TEXT DEFAULT 'UNCLASSIFIED',
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    query TEXT,
                    enhanced_query TEXT,
                    user_feedback REAL,
                    context TEXT,
                    outcome TEXT,
                    domain TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS enhancement_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT,
                    enhancement_template TEXT,
                    success_rate REAL,
                    usage_count INTEGER DEFAULT 0,
                    domain TEXT
                )
            ''')
            
            # Indexes for fast retrieval
            conn.execute('CREATE INDEX IF NOT EXISTS idx_domain ON knowledge_nodes(domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_relevance ON knowledge_nodes(relevance_score DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_access ON knowledge_nodes(last_accessed DESC)')
            
    async def add_knowledge(self, content: str, domain: KnowledgeDomain, 
                          embeddings: Optional[np.ndarray] = None) -> str:
        """Add new knowledge with compression and indexing"""
        # Generate ID and compress content
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        node_id = f"{domain.value}_{content_hash}"
        
        compressed = zlib.compress(content.encode('utf-8'), level=9)
        
        # Generate embeddings if not provided
        if embeddings is None:
            embeddings = await self._generate_embeddings(content)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO knowledge_nodes 
                (id, domain, content_hash, compressed_content, last_accessed)
                VALUES (?, ?, ?, ?, ?)
            ''', (node_id, domain.value, content_hash, compressed, datetime.utcnow()))
        
        # Update indexes
        self.domain_indexes[domain].add(node_id)
        self._update_embeddings_index(node_id, embeddings)
        
        # Check storage limits and prune if necessary
        await self._enforce_storage_limits()
        
        return node_id
    
    async def retrieve(self, query: str, domain: Optional[KnowledgeDomain] = None,
                      top_k: int = 5) -> List[Tuple[str, float]]:
        """Retrieve relevant knowledge using semantic search"""
        # Generate query embeddings
        query_embeddings = await self._generate_embeddings(query)
        
        # Search in domain-specific index if specified
        if domain:
            candidate_ids = self.domain_indexes[domain]
        else:
            candidate_ids = self._get_all_node_ids()
        
        # Semantic similarity search
        similarities = []
        for node_id in candidate_ids:
            node_embeddings = self._get_embeddings(node_id)
            if node_embeddings is not None:
                similarity = self._cosine_similarity(query_embeddings, node_embeddings)
                similarities.append((node_id, similarity))
        
        # Get top-k results
        top_results = heapq.nlargest(top_k, similarities, key=lambda x: x[1])
        
        # Retrieve and decompress content
        results = []
        with sqlite3.connect(self.db_path) as conn:
            for node_id, similarity in top_results:
                cursor = conn.execute('''
                    SELECT compressed_content, relevance_score 
                    FROM knowledge_nodes WHERE id = ?
                ''', (node_id,))
                
                row = cursor.fetchone()
                if row:
                    compressed_content, relevance = row
                    content = zlib.decompress(compressed_content).decode('utf-8')
                    
                    # Update access patterns
                    conn.execute('''
                        UPDATE knowledge_nodes 
                        SET access_count = access_count + 1, 
                            last_accessed = ?
                        WHERE id = ?
                    ''', (datetime.utcnow(), node_id))
                    
                    # Combine similarity and relevance scores
                    final_score = similarity * 0.7 + relevance * 0.3
                    results.append((content, final_score))
        
        return results
    
    async def learn_from_interaction(self, event: LearningEvent):
        """Learn from user interactions to improve future enhancements"""
        # Store learning event
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO learning_events 
                (timestamp, query, enhanced_query, user_feedback, context, outcome, domain)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.timestamp, event.query, event.enhanced_query,
                event.user_feedback, json.dumps(event.context),
                event.outcome, event.domain.value
            ))
        
        # Extract and store patterns if feedback is positive
        if event.user_feedback and event.user_feedback > 0.5:
            pattern_data = event.to_knowledge_update()
            await self._update_enhancement_patterns(pattern_data, event.domain)
        
        # Buffer for batch processing
        self.learning_buffer.append(event)
        
        # Process buffer when it reaches threshold
        if len(self.learning_buffer) >= 10:
            await self._process_learning_buffer()
    
    async def _process_learning_buffer(self):
        """Process accumulated learning events to update knowledge base"""
        if not self.learning_buffer:
            return
        
        # Group by domain and pattern
        domain_patterns = defaultdict(list)
        for event in self.learning_buffer:
            domain_patterns[event.domain].append(event.to_knowledge_update())
        
        # Update patterns and strategies
        with sqlite3.connect(self.db_path) as conn:
            for domain, patterns in domain_patterns.items():
                for pattern_data in patterns:
                    # Check if pattern exists
                    cursor = conn.execute('''
                        SELECT id, success_rate, usage_count 
                        FROM enhancement_patterns 
                        WHERE pattern = ? AND domain = ?
                    ''', (pattern_data['pattern'], domain.value))
                    
                    row = cursor.fetchone()
                    if row:
                        # Update existing pattern
                        pattern_id, current_rate, usage = row
                        new_rate = (current_rate * usage + pattern_data['quality_score']) / (usage + 1)
                        
                        conn.execute('''
                            UPDATE enhancement_patterns 
                            SET success_rate = ?, usage_count = usage_count + 1
                            WHERE id = ?
                        ''', (new_rate, pattern_id))
                    else:
                        # Create new pattern
                        conn.execute('''
                            INSERT INTO enhancement_patterns 
                            (pattern, enhancement_template, success_rate, domain)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            pattern_data['pattern'],
                            pattern_data['enhancement'],
                            pattern_data['quality_score'],
                            domain.value
                        ))
        
        # Clear buffer
        self.learning_buffer.clear()
    
    async def sync_with_online(self, online_knowledge: List[Dict[str, Any]]):
        """Sync with online knowledge base when connectivity is restored"""
        sync_stats = {
            'added': 0,
            'updated': 0,
            'conflicts': 0
        }
        
        for item in online_knowledge:
            try:
                # Check if exists locally
                node_id = item.get('id')
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'SELECT version, content_hash FROM knowledge_nodes WHERE id = ?',
                        (node_id,)
                    )
                    local_data = cursor.fetchone()
                    
                    if local_data:
                        local_version, local_hash = local_data
                        remote_version = item.get('version', 1)
                        
                        if remote_version > local_version:
                            # Update with newer version
                            await self._update_knowledge_node(item)
                            sync_stats['updated'] += 1
                        elif remote_version < local_version:
                            # Local is newer - mark for upload
                            sync_stats['conflicts'] += 1
                    else:
                        # Add new knowledge
                        await self.add_knowledge(
                            item['content'],
                            KnowledgeDomain(item['domain']),
                            item.get('embeddings')
                        )
                        sync_stats['added'] += 1
                        
            except Exception as e:
                print(f"Sync error for item {item.get('id')}: {e}")
                continue
        
        # Prune old or irrelevant content
        await self._prune_stale_knowledge()
        
        return sync_stats
    
    async def _enforce_storage_limits(self):
        """Enforce storage limits based on tier by pruning least relevant content"""
        current_size = self._calculate_storage_size()
        limit = self.storage_limits[self.storage_tier]
        
        if current_size > limit * 0.9:  # 90% threshold
            # Calculate how much to prune
            target_size = limit * 0.7  # Prune to 70%
            size_to_remove = current_size - target_size
            
            # Get candidates for removal (least relevant, oldest)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, compressed_content 
                    FROM knowledge_nodes 
                    ORDER BY relevance_score ASC, last_accessed ASC
                    LIMIT 1000
                ''')
                
                removed_size = 0
                for node_id, compressed_content in cursor:
                    if removed_size >= size_to_remove:
                        break
                    
                    # Remove node
                    conn.execute('DELETE FROM knowledge_nodes WHERE id = ?', (node_id,))
                    self._remove_from_indexes(node_id)
                    removed_size += len(compressed_content)
    
    def _calculate_storage_size(self) -> int:
        """Calculate total storage size used"""
        total_size = 0
        
        # Database size
        if self.db_path.exists():
            total_size += self.db_path.stat().st_size
        
        # Index size
        if self.index_path.exists():
            total_size += self.index_path.stat().st_size
        
        # Embeddings size
        if self.embeddings_path.exists():
            total_size += self.embeddings_path.stat().st_size
        
        return total_size
    
    async def _generate_embeddings(self, text: str) -> np.ndarray:
        """Generate embeddings for text (simplified for offline use)"""
        # In production, this would use a small local embedding model
        # For demo, using simple TF-IDF-like approach
        words = text.lower().split()
        
        # Simple word frequency vector (would be replaced with real embeddings)
        vocab_size = 1000
        embeddings = np.zeros(vocab_size)
        
        for word in words:
            idx = hash(word) % vocab_size
            embeddings[idx] += 1
        
        # Normalize
        norm = np.linalg.norm(embeddings)
        if norm > 0:
            embeddings = embeddings / norm
        
        return embeddings
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _load_enhancement_strategies(self) -> Dict[str, Any]:
        """Load pre-computed enhancement strategies"""
        strategies_path = self.storage_path / "strategies.json"
        
        if strategies_path.exists():
            with open(strategies_path, 'r') as f:
                return json.load(f)
        
        # Default strategies
        return {
            "technical": {
                "patterns": ["how to", "implement", "configure", "debug", "optimize"],
                "enhancements": ["Add specific constraints", "Include performance metrics", "Specify target environment"]
            },
            "military": {
                "patterns": ["mission", "operation", "tactical", "strategic", "deployment"],
                "enhancements": ["Add operational context", "Specify ROE", "Include force composition"]
            },
            "medical": {
                "patterns": ["diagnose", "treat", "symptoms", "medication", "procedure"],
                "enhancements": ["Add patient context", "Specify urgency", "Include contraindications"]
            }
        }
    
    def export_for_edge_deployment(self, output_path: str, target_size_mb: int = 100):
        """Export optimized knowledge base for edge devices"""
        export_path = Path(output_path)
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Calculate compression ratio needed
        current_size_mb = self._calculate_storage_size() / (1024**2)
        compression_ratio = min(1.0, target_size_mb / current_size_mb)
        
        # Select most relevant content up to size limit
        with sqlite3.connect(self.db_path) as conn:
            # Create compact database
            compact_db_path = export_path / "knowledge_compact.db"
            compact_conn = sqlite3.connect(compact_db_path)
            
            # Copy schema
            for line in conn.iterdump():
                if line.startswith('CREATE'):
                    compact_conn.execute(line)
            
            # Copy most relevant content
            cursor = conn.execute('''
                SELECT * FROM knowledge_nodes 
                ORDER BY relevance_score DESC, access_count DESC
            ''')
            
            exported_size = 0
            target_size_bytes = target_size_mb * 1024**2
            
            for row in cursor:
                # Estimate row size
                row_size = sum(len(str(field)) if field else 0 for field in row)
                
                if exported_size + row_size > target_size_bytes:
                    break
                
                # Insert into compact database
                placeholders = ','.join(['?' for _ in row])
                compact_conn.execute(f'INSERT INTO knowledge_nodes VALUES ({placeholders})', row)
                exported_size += row_size
            
            compact_conn.commit()
            compact_conn.close()
        
        # Create metadata file
        metadata = {
            'export_date': datetime.utcnow().isoformat(),
            'source_size_mb': current_size_mb,
            'target_size_mb': target_size_mb,
            'compression_ratio': compression_ratio,
            'storage_tier': self.storage_tier.value,
            'node_count': self._get_node_count()
        }
        
        with open(export_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return export_path
    
    def _get_node_count(self) -> int:
        """Get total number of knowledge nodes"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM knowledge_nodes')
            return cursor.fetchone()[0]
    
    def _get_all_node_ids(self) -> Set[str]:
        """Get all node IDs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT id FROM knowledge_nodes')
            return {row[0] for row in cursor}
    
    def _update_embeddings_index(self, node_id: str, embeddings: np.ndarray):
        """Update embeddings index"""
        # In production, this would use a proper vector database
        # For demo, storing in binary file with simple index
        embeddings_data = embeddings.astype(np.float32).tobytes()
        
        # Append to embeddings file
        with open(self.embeddings_path, 'ab') as f:
            offset = f.tell()
            f.write(embeddings_data)
        
        # Update index
        self.index_cache[node_id] = {
            'offset': offset,
            'size': len(embeddings_data)
        }
    
    def _get_embeddings(self, node_id: str) -> Optional[np.ndarray]:
        """Retrieve embeddings for a node"""
        if node_id not in self.index_cache:
            return None
        
        index_info = self.index_cache[node_id]
        
        with open(self.embeddings_path, 'rb') as f:
            f.seek(index_info['offset'])
            data = f.read(index_info['size'])
            
        return np.frombuffer(data, dtype=np.float32)
    
    def _remove_from_indexes(self, node_id: str):
        """Remove node from all indexes"""
        # Remove from domain indexes
        for domain_set in self.domain_indexes.values():
            domain_set.discard(node_id)
        
        # Remove from embeddings index
        self.index_cache.pop(node_id, None)
    
    async def _prune_stale_knowledge(self):
        """Prune knowledge that hasn't been accessed recently"""
        cutoff_date = datetime.utcnow() - timedelta(days=180)  # 6 months
        
        with sqlite3.connect(self.db_path) as conn:
            # Find stale nodes
            cursor = conn.execute('''
                SELECT id FROM knowledge_nodes 
                WHERE last_accessed < ? AND relevance_score < 0.5
            ''', (cutoff_date,))
            
            stale_ids = [row[0] for row in cursor]
            
            # Remove stale nodes
            for node_id in stale_ids:
                conn.execute('DELETE FROM knowledge_nodes WHERE id = ?', (node_id,))
                self._remove_from_indexes(node_id)


class AdaptiveLearningEngine:
    """
    Continuous learning engine that improves enhancement strategies over time
    """
    
    def __init__(self, knowledge_base: OfflineKnowledgeBase):
        self.knowledge_base = knowledge_base
        self.strategy_performance = defaultdict(lambda: {'success': 0, 'total': 0})
        self.user_preferences = defaultdict(dict)
        
    async def learn_from_feedback(self, query: str, enhanced: str, 
                                feedback: float, context: Dict[str, Any]):
        """Learn from user feedback to improve future enhancements"""
        # Create learning event
        event = LearningEvent(
            timestamp=datetime.utcnow(),
            query=query,
            enhanced_query=enhanced,
            user_feedback=feedback,
            context=context,
            outcome="success" if feedback > 0.5 else "failure",
            domain=self._detect_domain(query)
        )
        
        # Update knowledge base
        await self.knowledge_base.learn_from_interaction(event)
        
        # Update strategy performance
        strategy = context.get('strategy_used', 'unknown')
        self.strategy_performance[strategy]['total'] += 1
        if feedback > 0.5:
            self.strategy_performance[strategy]['success'] += 1
        
        # Learn user preferences
        user_id = context.get('user_id', 'anonymous')
        self._update_user_preferences(user_id, query, enhanced, feedback)
    
    def _detect_domain(self, query: str) -> KnowledgeDomain:
        """Detect domain from query content"""
        query_lower = query.lower()
        
        domain_keywords = {
            KnowledgeDomain.MILITARY: ['mission', 'tactical', 'deployment', 'operation', 'combat'],
            KnowledgeDomain.TECHNICAL: ['code', 'system', 'implement', 'debug', 'api'],
            KnowledgeDomain.MEDICAL: ['patient', 'treatment', 'diagnosis', 'symptom', 'medication'],
            KnowledgeDomain.CYBERSECURITY: ['security', 'vulnerability', 'encryption', 'threat', 'breach'],
            KnowledgeDomain.LOGISTICS: ['supply', 'transport', 'inventory', 'distribution', 'warehouse'],
            KnowledgeDomain.COMMUNICATIONS: ['radio', 'signal', 'frequency', 'transmission', 'network']
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return domain
        
        return KnowledgeDomain.GENERAL
    
    def _update_user_preferences(self, user_id: str, query: str, 
                               enhanced: str, feedback: float):
        """Update user-specific preferences"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                'style_preferences': {},
                'domain_expertise': defaultdict(float),
                'average_satisfaction': 0.0,
                'interaction_count': 0
            }
        
        prefs = self.user_preferences[user_id]
        
        # Update interaction count and satisfaction
        prefs['interaction_count'] += 1
        prefs['average_satisfaction'] = (
            (prefs['average_satisfaction'] * (prefs['interaction_count'] - 1) + feedback) /
            prefs['interaction_count']
        )
        
        # Detect style preferences
        if len(enhanced) > len(query) * 2:
            prefs['style_preferences']['verbose'] = prefs['style_preferences'].get('verbose', 0) + feedback
        else:
            prefs['style_preferences']['concise'] = prefs['style_preferences'].get('concise', 0) + feedback
        
        # Update domain expertise
        domain = self._detect_domain(query)
        prefs['domain_expertise'][domain.value] += feedback
    
    def get_best_strategy(self, query: str, context: Dict[str, Any]) -> str:
        """Get the best enhancement strategy based on historical performance"""
        # Get user preferences if available
        user_id = context.get('user_id', 'anonymous')
        user_prefs = self.user_preferences.get(user_id, {})
        
        # Score each strategy
        strategy_scores = {}
        
        for strategy, performance in self.strategy_performance.items():
            if performance['total'] > 0:
                success_rate = performance['success'] / performance['total']
                
                # Adjust score based on user preferences
                score = success_rate
                
                # Boost score if strategy aligns with user style
                if 'verbose' in strategy and user_prefs.get('style_preferences', {}).get('verbose', 0) > 0:
                    score *= 1.2
                elif 'concise' in strategy and user_prefs.get('style_preferences', {}).get('concise', 0) > 0:
                    score *= 1.2
                
                strategy_scores[strategy] = score
        
        # Return best strategy or default
        if strategy_scores:
            return max(strategy_scores.items(), key=lambda x: x[1])[0]
        
        return "default_enhancement"


# Example usage
async def demonstrate_offline_knowledge():
    """Demonstrate offline knowledge base capabilities"""
    
    # Initialize knowledge base
    kb = OfflineKnowledgeBase(
        storage_path="./offline_knowledge",
        storage_tier=StorageTier.COMPACT
    )
    
    # Add military operational knowledge
    await kb.add_knowledge(
        "Field communication protocols: Use frequency hopping spread spectrum (FHSS) "
        "for jam-resistant communications. Primary: 30-88 MHz VHF, Secondary: 225-400 MHz UHF. "
        "Emergency: 121.5 MHz guard frequency.",
        KnowledgeDomain.MILITARY
    )
    
    await kb.add_knowledge(
        "Tactical medical priorities: 1) Massive hemorrhage control (tourniquet within 60 seconds), "
        "2) Airway management, 3) Respiratory support, 4) Circulation, 5) Hypothermia prevention. "
        "Golden hour critical for CASEVAC.",
        KnowledgeDomain.MEDICAL
    )
    
    await kb.add_knowledge(
        "Offline navigation: Primary: GPS with cached maps. Secondary: Compass bearing + pace count. "
        "Tertiary: Celestial navigation. Terrain association as continuous backup. "
        "Grid reference format: MGRS 10-digit minimum.",
        KnowledgeDomain.MILITARY
    )
    
    # Simulate query in desert scenario
    print("Scenario: Zero connectivity, field medical emergency")
    print("-" * 60)
    
    query = "soldier injured need immediate treatment protocol"
    results = await kb.retrieve(query, domain=KnowledgeDomain.MEDICAL, top_k=3)
    
    print(f"Query: {query}")
    print(f"Retrieved knowledge:")
    for i, (content, score) in enumerate(results):
        print(f"{i+1}. (Score: {score:.3f}) {content[:100]}...")
    
    # Simulate learning from interaction
    learning_engine = AdaptiveLearningEngine(kb)
    
    await learning_engine.learn_from_feedback(
        query=query,
        enhanced="Apply immediate hemorrhage control with tourniquet if bleeding from extremity. "
                 "Follow MARCH protocol: Massive hemorrhage, Airway, Respiration, Circulation, Hypothermia. "
                 "Request immediate CASEVAC on emergency frequency 121.5 MHz.",
        feedback=0.9,  # Positive feedback
        context={
            'user_id': 'medic_001',
            'location': 'field',
            'urgency': 'critical',
            'strategy_used': 'medical_emergency_enhancement'
        }
    )
    
    # Export for edge device
    print("\nExporting for edge deployment...")
    export_path = kb.export_for_edge_deployment(
        "./edge_deployment",
        target_size_mb=50  # 50MB limit for tablet
    )
    print(f"Exported to: {export_path}")
    
    # Show sync capability
    print("\nSimulating sync when connectivity restored...")
    sync_stats = await kb.sync_with_online([
        {
            'id': 'military_update_001',
            'content': 'Updated ROE: Positive identification required before engagement.',
            'domain': 'military',
            'version': 2
        }
    ])
    print(f"Sync complete: {sync_stats}")


if __name__ == "__main__":
    asyncio.run(demonstrate_offline_knowledge())
