def menu():
    print("===============================")
    print("Lost and Found Management System")
    print("===============================\n")
    print("What are you here for?")
    print("1. Find a lost item")
    print("2. Report a found item\n")

    user_input = input("Enter your choice (1 or 2): ")
    
    if not user_input.isdigit() or int(user_input) not in [1, 2]:
        print("\nInvalid input. Please enter 1 or 2.\n")
        return menu()
    
    if user_input == "1":
        print("\nYou selected: Find a lost item\n")
        return "lost"
    else:
        print("\nYou selected: Report a found item\n")
        return "found"

def get_item_description():
    item_type = input("Enter the item type: ")
    item_color = input("Enter the item color: ")
    item_brand = input("Enter the item brand: ")
    item_description = input("Enter the item unique description: ")

    return item_type, item_color, item_brand, item_description

def get_datetimelocation():
    datetime = input("Enter the date and time: ")
    location = input("Enter the location: ")

    return datetime, location

def invalid_inputs(item_data):
    if not item_data["item_type"]["value"]:
        item_data["item_type"]["value"] = input("Enter the item type: ") 
    if not item_data["item_colour"]["value"]:
        item_data["item_colour"]["value"] = input("Enter the item color: ")
    if not item_data["item_brand"]["value"]:
        item_data["item_brand"]["value"] = input("Enter the item brand: ")
    if not item_data["item_unique_info"]["value"]:
        item_data["item_unique_info"]["value"] = input("Enter the item unique description: ")
    if not item_data["datetime"]["value"]:
        item_data["datetime"]["value"] = input("Enter the date and time: ")
    if not item_data["location"]["value"]:
        item_data["location"]["value"] = input("Enter the location: ")
    return item_data


def display_matches(top_matches):
    print("Displaying top five matches...\n")
    for lines in top_matches:
        print(lines)

def items_not_found():
    print("No matching items found. Please try again later or report a found item.")

