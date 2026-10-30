"""Export selected competitions as three flat, analysis-ready CSV tables."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from arena.benchmark_export import export

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories',nargs='*',type=Path,help='Competition directories; default: all runs with experiment.json')
    parser.add_argument('--runs',type=Path,default=ROOT/'runs')
    parser.add_argument('--out',type=Path,required=True,help='New output directory')
    args=parser.parse_args()
    runs=args.directories or [p.parent for p in sorted(args.runs.glob('*/experiment.json')) if not (p.parent/'export.json').exists()]
    if not runs: parser.error('No competitions found')
    print(json.dumps(export(runs,args.out),indent=2))
