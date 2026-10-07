import io_manager

# menu_selection = io_manager.menu() #output: "lost" or "found"
# item_type, item_color, item_brand, item_description = io_manager.get_item_description()
# item_datetime, item_location = io_manager.get_datetimelocation()

#sample invalid input data for testing
input_data = {
"report_type": "lost",
"item_description": {
"value": "Samsung Galaxy S25",
"confidence": 1.0
},
"item_type": {
"value": "phone",
"confidence": 1.0
},
"item_colour": {
"value": None,
"confidence": 1.0
},
"item_brand": {
"value": "Samsung",
"confidence": 1.0
},
"item_unique_info": {
"value": None,
"confidence": 0.0
},
"datetime": {
"value": "2026-10-01T15:30",
"confidence": 1.0
},
"location": {
"value": "SIT Punggol food court",
"confidence": 1.0
}
}

updated_item_data = io_manager.invalid_inputs(input_data)
print(updated_item_data)