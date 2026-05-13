import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="sunbeam-valet")
    sub = parser.add_subparsers(dest="command")

    dash = sub.add_parser("dashboard", help="start the bug triage dashboard")
    dash.add_argument(
        "-p",
        "--port",
        type=int,
        default=8473,
        help="port to listen on (default: 8473)",
    )
    dash.add_argument(
        "--host",
        default="127.0.0.1",
        help="host to bind to (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    if args.command == "dashboard":
        from sunbeam_valet.dashboard.app import serve

        serve(host=args.host, port=args.port)
    else:
        print("Hello from sunbeam-valet!")


if __name__ == "__main__":
    main()
