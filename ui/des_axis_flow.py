from core.axis.bridge import execute_axis_request


def run():
    des_output = {
        "friction_type": "information_gap",
        "details": {
            "next_action": "Review the clarified decision information and choose one next step.",
        },
    }

    response = execute_axis_request(
        des_output=des_output,
        trigger="User asked for pricing clarity before choosing a plan.",
        operator_id="local-operator",
    )

    print(response)


if __name__ == "__main__":
    run()
