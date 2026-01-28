"""
Advanced Macro Trading Terminal - Punkt Wejścia
================================================

To jest główny punkt wejścia aplikacji.
Inicjalizuje logowanie, parsuje argumenty wiersza poleceń
i uruchamia serwer FastAPI.

Użycie:
    python main.py                    # Uruchom z domyślnymi ustawieniami
    python main.py --port 8080        # Własny port
    python main.py --debug            # Tryb debugowania
    python main.py --host 0.0.0.0     # Własny host
"""

import argparse
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logging, get_logger


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the application.
    
    Returns:
        argparse.Namespace: Parsed arguments with host, port, and debug settings.
    """
    parser = argparse.ArgumentParser(
        description="Advanced Macro Trading Terminal - Professional REST API for economic indicator analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                    Start server with defaults (localhost:8000)
    python main.py --port 8080        Start on port 8080
    python main.py --debug            Enable debug mode with auto-reload
    python main.py --host 0.0.0.0     Allow external connections
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with auto-reload"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the application.
    
    Initializes logging, displays startup banner, checks API keys,
    and starts the uvicorn server.
    """
    args = parse_arguments()
    
    # Setup logging
    setup_logging(level=args.log_level)
    logger = get_logger(__name__)
    
    # Display startup banner
    print("=" * 60)
    print("  [*] Advanced Macro Trading Terminal v3.0")
    print("=" * 60)
    
    # Check API keys
    from dotenv import load_dotenv
    load_dotenv()
    
    fred_key = os.getenv("FRED_API_KEY")
    news_key = os.getenv("NEWS_API_KEY")
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    print(f"  [+] FRED API:      {'OK' if fred_key else 'MISSING'}")
    print(f"  [+] News API:      {'OK' if news_key else 'MISSING'}")
    print(f"  [+] Perplexity AI: {'OK' if perplexity_key else 'MISSING'}")
    print("=" * 60)
    print(f"  [>] Starting server at http://{args.host}:{args.port}")
    print(f"  [>] Log level: {args.log_level}")
    print(f"  [>] Debug mode: {'ON' if args.debug else 'OFF'}")
    print("=" * 60)
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    # Start server
    import uvicorn
    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=args.debug,
        log_level=args.log_level.lower()
    )


if __name__ == "__main__":
    main()
