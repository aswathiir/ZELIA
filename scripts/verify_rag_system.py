"""
ZELIA - Real-time Verification Tool
Shows live results from RAG system to verify everything is working
"""
import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

def test_web_scraper():
    """Test web scraper service"""
    console.print("\n[bold cyan]═══ Testing Web Scraper Service ═══[/bold cyan]\n")
    
    try:
        # Test 1: Get stats
        console.print("[yellow]1. Getting service statistics...[/yellow]")
        response = requests.get("http://localhost:8008/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            console.print(f"   ✓ Total Schemes: [green]{stats['total_schemes']}[/green]")
            console.print(f"   ✓ Categories: [green]{', '.join(stats['categories'][:5])}...[/green]")
            console.print(f"   ✓ Data Source: [green]{stats['data_source']}[/green]")
        else:
            console.print(f"   ✗ Failed: {response.status_code}", style="red")
            return False
        
        # Test 2: Search for pension
        console.print("\n[yellow]2. Searching for 'pension schemes'...[/yellow]")
        response = requests.post(
            "http://localhost:8008/scrape/schemes",
            json={"query": "pension", "max_results": 3},
            timeout=5
        )
        if response.status_code == 200:
            results = response.json()
            console.print(f"   ✓ Found: [green]{len(results)} schemes[/green]\n")
            
            # Display results in table
            table = Table(title="Search Results")
            table.add_column("Title", style="cyan")
            table.add_column("Score", style="magenta")
            table.add_column("Category", style="green")
            
            for r in results:
                table.add_row(
                    r['title'][:50] + "..." if len(r['title']) > 50 else r['title'],
                    f"{r['relevance_score']:.2f}",
                    r['metadata']['category']
                )
            
            console.print(table)
            return True
        else:
            console.print(f"   ✗ Search failed: {response.status_code}", style="red")
            return False
            
    except requests.exceptions.ConnectionError:
        console.print("   ✗ Cannot connect to web-scraper service", style="red")
        console.print("   → Run: docker compose up -d web-scraper", style="yellow")
        return False
    except Exception as e:
        console.print(f"   ✗ Error: {e}", style="red")
        return False

def test_retrieval_service():
    """Test retrieval service (vector search)"""
    console.print("\n[bold cyan]═══ Testing Retrieval Service (Vector Search) ═══[/bold cyan]\n")
    
    try:
        # Test health
        console.print("[yellow]1. Checking service health...[/yellow]")
        response = requests.get("http://localhost:8007/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            console.print(f"   ✓ Status: [green]{health['status']}[/green]")
            console.print(f"   ✓ Index Size: [green]{health['index_size']} documents[/green]")
        else:
            console.print(f"   ✗ Health check failed: {response.status_code}", style="red")
            return False
        
        # Test vector search
        console.print("\n[yellow]2. Testing vector search for 'old age pension'...[/yellow]")
        response = requests.post(
            "http://localhost:8007/search",
            json={"query": "old age pension", "k": 3},
            timeout=5
        )
        if response.status_code == 200:
            results = response.json()
            console.print(f"   ✓ Found: [green]{len(results)} results[/green]\n")
            
            if results:
                table = Table(title="Vector Search Results")
                table.add_column("Content Preview", style="cyan")
                table.add_column("Score", style="magenta")
                table.add_column("Source", style="green")
                
                for r in results:
                    table.add_row(
                        r['content'][:60] + "...",
                        f"{r['score']:.4f}",
                        r['metadata'].get('source', 'N/A')[:30]
                    )
                
                console.print(table)
            return True
        else:
            console.print(f"   ✗ Search failed: {response.status_code}", style="red")
            return False
            
    except requests.exceptions.ConnectionError:
        console.print("   ✗ Cannot connect to retrieval service", style="red")
        console.print("   → Run: docker compose up -d retrieval-service", style="yellow")
        return False
    except Exception as e:
        console.print(f"   ✗ Error: {e}", style="red")
        return False

def test_hybrid_search():
    """Test hybrid search (vector + web)"""
    console.print("\n[bold cyan]═══ Testing Hybrid Search (Vector + Web) ═══[/bold cyan]\n")
    
    try:
        console.print("[yellow]Searching for 'housing scheme'...[/yellow]")
        response = requests.post(
            "http://localhost:8007/search/hybrid",
            json={"query": "housing scheme", "k": 5},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            stats = data['stats']
            
            console.print(f"   ✓ Vector results: [green]{stats['vector_results']}[/green]")
            console.print(f"   ✓ Web results: [green]{stats['web_results']}[/green]")
            console.print(f"   ✓ Total: [green]{stats['total']}[/green]")
            console.print(f"   ✓ Fallback used: [cyan]{stats['fallback_used']}[/cyan]\n")
            
            # Show top 3 results
            results = data['results'][:3]
            if results:
                table = Table(title="Top 3 Hybrid Results")
                table.add_column("Content", style="cyan")
                table.add_column("Score", style="magenta")
                table.add_column("Source Type", style="green")
                
                for r in results:
                    table.add_row(
                        r['content'][:50] + "...",
                        f"{r['score']:.4f}",
                        r['metadata'].get('source_type', 'N/A')
                    )
                
                console.print(table)
            return True
        else:
            console.print(f"   ✗ Hybrid search failed: {response.status_code}", style="red")
            return False
            
    except requests.exceptions.ConnectionError:
        console.print("   ✗ Cannot connect to retrieval service", style="red")
        return False
    except Exception as e:
        console.print(f"   ✗ Error: {e}", style="red")
        return False

def main():
    """Run all verification tests"""
    console.print(Panel.fit(
        "[bold green]ZELIA RAG System Verification[/bold green]\n"
        "Real-time testing to verify everything is working",
        border_style="green"
    ))
    
    results = {
        "Web Scraper": test_web_scraper(),
        "Retrieval Service": test_retrieval_service(),
        "Hybrid Search": test_hybrid_search()
    }
    
    # Summary
    console.print("\n[bold cyan]═══ Summary ═══[/bold cyan]\n")
    for service, status in results.items():
        status_text = "[green]✓ WORKING[/green]" if status else "[red]✗ NOT WORKING[/red]"
        console.print(f"  {service}: {status_text}")
    
    console.print("\n[bold]Next Steps:[/bold]")
    if all(results.values()):
        console.print("  [green]✓ All services are working correctly![/green]")
        console.print("  → You can now use the RAG system for scheme search")
    else:
        console.print("  [yellow]→ Start missing services with: docker compose up -d[/yellow]")
    
    console.print()

if __name__ == "__main__":
    main()
