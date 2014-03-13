import argparse
import probe_certs

def get_args():
    parser = argparse.ArgumentParser(description="Probe FDIC.gov for BO filers.")
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of total requests to FDIC.gov (default: None)"
        )
    parser.add_argument(
        '-a', '--all', 
        action='store_true',
        default=False, 
        help="Include inactive FDIC institutions in probe")

    return parser.parse_args()

def main():
    probe_certs.probe(get_args())

if __name__ == '__main__':
    main()
