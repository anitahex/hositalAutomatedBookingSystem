from app.agents.graph import graph, run_patient_chat


if __name__ == "__main__":
    test_input = "My skin is incredibly dry, peeling, and has developed itchy red scaly patches."
    output_state = run_patient_chat(test_input)

    print("\n=====================================================================")
    print("FINAL AGENT RESPONSE TO PATIENT:")
    print(output_state["final_response"])
    print("=====================================================================")
