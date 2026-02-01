```python
from services.utils.chain_of_table.informer import get_table_insight

input_data = {}
input_data[
    "file_path"] = "/Users/sarkarsaurabh.27/Documents/Projects/chicoryai/data/dh/chis/AskCHISResults202406031042.xlsx"
# input_data["question"] = "What is the percentage of people who reported having high BP in 2019 at Nevada?"
# input_data["question"] = "For how many locations did people report having high BP in 2019?"
input_data["question"] = "Name all the columns for the people report having high BP in 2019?"

result = get_table_insight(input_data)
print(result)
```