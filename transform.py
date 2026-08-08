def calculate_net_revenue(gross_revenue, discount):
    return gross_revenue - discount


if __name__ == "__main__":
    result = calculate_net_revenue(100_000, 20_000)
    print(f"Net revenue: {result}")