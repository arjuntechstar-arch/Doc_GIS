from pathlib import Path
import sys
from dotenv import load_dotenv
root=Path(__file__).resolve().parents[1]
load_dotenv(root/'.env')
sys.path.insert(0,str(root/'src/backend'))
from healthcare_gis.bootstrap import main
main()
