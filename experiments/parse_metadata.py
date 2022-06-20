import sys
sys.path.insert(1, 'src')

from app.utils import get_coordinate_from_metadata

coordinates = get_coordinate_from_metadata("e8a0f193-ac27-46ca-9ac8-920549a7254e", "722-1005")

print(str(coordinates))