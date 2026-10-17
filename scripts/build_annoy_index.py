"""
Build Annoy Index for Ultra-Fast Vector Search
Purpose: Creates local Annoy index (10-20ms search time)
"""

import json
import os
from pathlib import Path
from annoy import AnnoyIndex
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import time

console = Console()

class AnnoyIndexBuilder:
    def __init__(self, embedding_dim=384, n_trees=100):
        """Initialize Annoy index builder"""
        self.embedding_dim = embedding_dim
        self.n_trees = n_trees
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = AnnoyIndex(embedding_dim, 'angular')
        self.metadata = []
        
    def load_schemes(self, data_file):
        """Load schemes from JSON"""
        console.print(f"📂 Loading schemes from {data_file}...", style="cyan")
        
        if not os.path.exists(data_file):
            console.print(f"❌ File not found: {data_file}", style="red")
            return []
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        schemes = data.get('schemes', [])
        console.print(f"✅ Loaded {len(schemes)} schemes", style="green")
        return schemes
    
    def build_index(self, schemes):
        """Build Annoy index from schemes"""
        console.print("\n🔨 Building Annoy index...", style="yellow bold")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            
            task = progress.add_task("Processing schemes...", total=len(schemes))
            
            for i, scheme in enumerate(schemes):
                # Create searchable text
                text_parts = [
                    scheme.get('name', ''),
                    scheme.get('description', ''),
                    scheme.get('category', ''),
                    ' '.join(scheme.get('keywords', [])),
                    ' '.join(scheme.get('eligibility', {}).get('criteria', []))
                ]
                searchable_text = ' '.join(filter(None, text_parts))
                
                # Generate embedding
                embedding = self.model.encode(searchable_text)
                
                # Add to Annoy index
                self.index.add_item(i, embedding)
                
                # Store metadata
                self.metadata.append({
                    "index": i,
                    "scheme_id": scheme.get('scheme_id', f'scheme_{i}'),
                    "name": scheme.get('name', ''),
                    "category": scheme.get('category', ''),
                    "state": scheme.get('state', ''),
                    "description": scheme.get('description', '')[:500],
                    "text": searchable_text[:1000]
                })
                
                progress.update(task, advance=1)
        
        # Build index with n_trees
        console.print(f"\n🌲 Building index with {self.n_trees} trees...", style="cyan")
        start_time = time.time()
        self.index.build(self.n_trees)
        build_time = time.time() - start_time
        
        console.print(f"✅ Index built in {build_time:.2f}s", style="green")
        return build_time
    
    def save_index(self, index_path, metadata_path):
        """Save Annoy index and metadata"""
        console.print("\n💾 Saving index files...", style="cyan")
        
        # Save Annoy index
        self.index.save(index_path)
        console.print(f"  ✓ Saved index: {index_path}", style="green")
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        console.print(f"  ✓ Saved metadata: {metadata_path}", style="green")
    
    def test_search(self, query, k=5):
        """Test search functionality"""
        console.print(f"\n🔍 Testing search: '{query}'", style="yellow bold")
        
        # Generate query embedding
        start_time = time.time()
        query_embedding = self.model.encode(query)
        
        # Search
        indices, distances = self.index.get_nns_by_vector(
            query_embedding, k, include_distances=True
        )
        search_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Display results
        console.print(f"\n⚡ Search time: {search_time:.2f}ms", style="cyan bold")
        console.print("\nResults:", style="yellow")
        
        for idx, dist in zip(indices, distances):
            similarity = 1 - (dist / 2)  # Convert distance to similarity
            metadata = self.metadata[idx]
            
            console.print(f"\n  [{metadata['index']}] {metadata['name']}", style="green bold")
            console.print(f"      Score: {similarity:.4f}", style="cyan")
            console.print(f"      Category: {metadata['category']}", style="white")
            console.print(f"      State: {metadata['state']}", style="white")
            console.print(f"      Description: {metadata['description'][:100]}...", style="dim")
        
        return search_time


def main():
    console.print("\n" + "="*70, style="cyan bold")
    console.print("  ZELIA ANNOY INDEX BUILDER", style="cyan bold")
    console.print("  Ultra-Fast Vector Search (10-20ms)", style="cyan bold")
    console.print("="*70 + "\n", style="cyan bold")
    
    # Paths
    project_root = Path(__file__).parent.parent
    data_file = project_root / "schemes_data" / "myscheme_dataset.json"
    output_dir = project_root / "backend" / "services" / "embedding-service"
    index_path = output_dir / "annoy_index.ann"
    metadata_path = output_dir / "annoy_metadata.json"
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build index
    builder = AnnoyIndexBuilder(embedding_dim=384, n_trees=100)
    
    # Load schemes
    schemes = builder.load_schemes(str(data_file))
    if not schemes:
        console.print("❌ No schemes loaded. Exiting.", style="red")
        return
    
    # Build index
    build_time = builder.build_index(schemes)
    
    # Save
    builder.save_index(str(index_path), str(metadata_path))
    
    # Test with sample queries
    console.print("\n" + "="*70, style="yellow bold")
    console.print("  TESTING INDEX", style="yellow bold")
    console.print("="*70 + "\n", style="yellow bold")
    
    test_queries = [
        "pension schemes for widows",
        "housing subsidy for poor",
        "scholarships for students",
        "farmer loan schemes"
    ]
    
    total_time = 0
    for query in test_queries:
        search_time = builder.test_search(query, k=3)
        total_time += search_time
    
    avg_time = total_time / len(test_queries)
    
    # Summary
    console.print("\n" + "="*70, style="green bold")
    console.print("  BUILD SUMMARY", style="green bold")
    console.print("="*70, style="green bold")
    console.print(f"\n✅ Total schemes indexed: {len(schemes)}", style="green")
    console.print(f"✅ Index dimension: {builder.embedding_dim}", style="green")
    console.print(f"✅ Number of trees: {builder.n_trees}", style="green")
    console.print(f"✅ Build time: {build_time:.2f}s", style="green")
    console.print(f"✅ Average search time: {avg_time:.2f}ms", style="green bold")
    console.print(f"✅ Index file: {index_path}", style="green")
    console.print(f"✅ Metadata file: {metadata_path}\n", style="green")
    
    if avg_time < 20:
        console.print("🎉 SUCCESS! Sub-20ms search achieved!", style="green bold")
    else:
        console.print("⚠️  Search time > 20ms. Consider increasing trees.", style="yellow")


if __name__ == "__main__":
    main()
