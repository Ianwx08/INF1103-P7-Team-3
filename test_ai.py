from ai_manager import extract_item_information


test_inputs = [
    "Airpod pro 3 with keychain with logo lost at Tampines Mall 15 July 2026 2.05pm",

    "Found blue wallet at Punggol MRT on 20 September 2026 at 7pm",

    "Lost black Samsung Galaxy S25 at SIT Punggol food court 1 October 2026 3.30pm",

    "Lost my AirPods Pro at Tampines Mall"
]


for test_input in test_inputs:

    print("\n====================================")
    print("INPUT:")
    print(test_input)

    try:

        result = extract_item_information(test_input)

        print("\nAI OUTPUT:")

        print(
            result.model_dump_json(
                indent=4
            )
        )

    except Exception as error:

        print("\nERROR:")
        print(error)