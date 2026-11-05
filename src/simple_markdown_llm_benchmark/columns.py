"""Column definitions for the order table that every benchmark table imitates.

Plausible tables use these definitions directly. Gibberish tables keep the column layout and each column's number of distinct values, and replace headers and values with random strings of one fixed length.
"""

import string
from dataclasses import dataclass

from simple_markdown_llm_benchmark.sampling import Space


@dataclass(frozen=True)
class ColumnSpec:
    header: str
    space: Space
    distinct: int | None
    """How many distinct values the column draws from, weighted by 1/rank. None makes it a key column: every row gets a different value."""


LOWERCASE = tuple(string.ascii_lowercase)
UPPERCASE = tuple(string.ascii_uppercase)
DIGITS = tuple(string.digits)
NONZERO_DIGITS = DIGITS[1:]


def numbers(start: int, stop: int) -> tuple[str, ...]:
    return tuple(str(n) for n in range(start, stop))


FIRST_NAMES = (
    "Aaliyah", "Abdul", "Ada", "Adrian", "Aiko", "Alba", "Aleksander", "Amara", "Anders", "Anika",
    "Arjun", "Astrid", "Beatriz", "Bilal", "Bruno", "Camila", "Carmen", "Chen", "Chidi", "Clara",
    "Dalia", "Daniel", "Dmitri", "Elena", "Elif", "Emeka", "Emil", "Esther", "Fatima", "Felix",
    "Freya", "Gabriel", "Grace", "Hamid", "Hana", "Hugo", "Ines", "Ingrid", "Isaac", "Ivan",
    "Jamal", "Jana", "Javier", "Jin", "Joao", "Jonas", "Julia", "Kai", "Kamala", "Karim",
    "Kenji", "Kofi", "Lars", "Layla", "Leon", "Lina", "Lucia", "Luis", "Maja", "Malik",
    "Mara", "Marco", "Mateo", "Mei", "Mila", "Nadia", "Naveen", "Nia", "Nikolai", "Noah",
    "Nora", "Olga", "Omar", "Oscar", "Priya", "Rafael", "Rania", "Ravi", "Rosa", "Ruth",
    "Samir", "Sara", "Selin", "Sofia", "Soren", "Tariq", "Tomas", "Uma", "Valentina", "Viktor",
    "Wei", "Yara", "Yusuf", "Zainab", "Zara", "Zoltan", "Aditi", "Bianca", "Cyrus", "Dara",
)  # fmt: skip

LAST_NAMES = (
    "Abara", "Adeyemi", "Almeida", "Andersen", "Bakker", "Banerjee", "Becker", "Bianchi", "Brandt", "Castillo",
    "Chowdhury", "Costa", "Dahl", "Demir", "Dimitrov", "Dubois", "Eriksen", "Esposito", "Farah", "Fischer",
    "Fonseca", "Garcia", "Gomes", "Gupta", "Haddad", "Hansen", "Hernandez", "Horvath", "Huang", "Ibrahim",
    "Ivanova", "Jansen", "Jensen", "Kaur", "Kim", "Koch", "Kowalski", "Kruger", "Larsen", "Lefebvre",
    "Lindqvist", "Lopez", "Mahmoud", "Marino", "Martins", "Mendes", "Moreau", "Morales", "Muller", "Nakamura",
    "Navarro", "Nguyen", "Nielsen", "Novak", "Nowak", "Okafor", "Olsen", "Ortiz", "Osei", "Ozturk",
    "Park", "Patel", "Pereira", "Petrov", "Popescu", "Quinn", "Ramos", "Rao", "Reyes", "Ricci",
    "Rossi", "Ruiz", "Saito", "Santos", "Schmidt", "Schneider", "Sato", "Silva", "Singh", "Sokolov",
    "Suzuki", "Szabo", "Tanaka", "Torres", "Tran", "Vale", "Varga", "Vasquez", "Vogel", "Wagner",
    "Wang", "Weber", "Wojcik", "Yamamoto", "Yilmaz", "Young", "Zhang", "Ziegler", "Zimmermann", "Zubiri",
)  # fmt: skip

WORDS = (
    "amber", "anchor", "arrow", "aspen", "atlas", "birch", "bison", "blaze", "breeze", "brook",
    "cedar", "cinder", "cloud", "clover", "comet", "coral", "crane", "crest", "dawn", "delta",
    "drift", "dune", "ember", "falcon", "fern", "fjord", "flint", "frost", "garnet", "glade",
    "granite", "grove", "harbor", "hazel", "heron", "hollow", "indigo", "iris", "ivy", "jade",
    "juniper", "kestrel", "lagoon", "lark", "linden", "lotus", "lunar", "maple", "marsh", "meadow",
    "mesa", "mist", "moss", "nectar", "nimbus", "oak", "onyx", "orbit", "otter", "pebble",
    "pine", "plume", "prairie", "quartz", "quill", "raven", "reed", "ridge", "river", "robin",
    "rowan", "sable", "sage", "shore", "sierra", "slate", "solar", "sparrow", "spruce", "stone",
    "storm", "summit", "swift", "thistle", "thorn", "tide", "timber", "topaz", "tundra", "vale",
    "velvet", "willow", "wren", "zephyr", "basil", "canyon", "dusk", "echo", "glacier", "lumen",
)  # fmt: skip

CAPITALIZED_WORDS = tuple(word.capitalize() for word in WORDS)

EMAIL_DOMAINS = ("example.com", "example.net", "example.org", "mail.example", "post.example")

CITY_PREFIXES = (
    "Ash", "Bel", "Brook", "Cal", "Clear", "Dun", "East", "Elm", "Fair", "Glen",
    "Green", "Hart", "High", "Kings", "Lake", "Mill", "North", "Oak", "Port", "Red",
    "Rock", "Silver", "South", "Stone", "West",
)  # fmt: skip

CITY_SUFFIXES = (
    "bridge", "brook", "burg", "bury", "dale", "field", "ford", "gate", "haven", "hill",
    "holm", "ley", "mouth", "port", "stead", "ton", "vale", "view", "ville", "wick",
    "wood", "worth", "cliff", "moor", "shire",
)  # fmt: skip

COUNTRIES = (
    "Argentina", "Australia", "Austria", "Belgium", "Brazil", "Canada", "Chile", "Colombia", "Czechia", "Denmark",
    "Egypt", "Finland", "France", "Germany", "Ghana", "Greece", "Hungary", "India", "Indonesia", "Ireland",
    "Italy", "Japan", "Kenya", "Malaysia", "Mexico", "Morocco", "Netherlands", "New Zealand", "Nigeria", "Norway",
    "Peru", "Philippines", "Poland", "Portugal", "Romania", "South Korea", "Spain", "Sweden", "Turkey", "Vietnam",
)  # fmt: skip

PRODUCT_ADJECTIVES = (
    "Bamboo", "Brass", "Canvas", "Ceramic", "Classic", "Compact", "Copper", "Cotton", "Deluxe", "Ergonomic",
    "Folding", "Glass", "Granite", "Insulated", "Leather", "Linen", "Marble", "Matte", "Modular", "Oak",
    "Portable", "Recycled", "Rugged", "Silicone", "Slim", "Smart", "Steel", "Titanium", "Walnut", "Wool",
)  # fmt: skip

PRODUCT_NOUNS = (
    "Backpack", "Blanket", "Bottle", "Bowl", "Candle", "Chair", "Clock", "Cutting Board", "Desk Lamp", "Doormat",
    "Frame", "Grinder", "Headphones", "Jacket", "Kettle", "Keyboard", "Ladle", "Mirror", "Mug", "Notebook",
    "Pan", "Pillow", "Planter", "Rug", "Scarf", "Shelf", "Speaker", "Stool", "Teapot", "Wallet",
)  # fmt: skip

COMPANY_SUFFIXES = ("Ltd", "Inc", "GmbH", "Group", "Labs", "Supply", "Trading", "Partners")
STREET_TYPES = ("Street", "Lane", "Road", "Avenue", "Way", "Court")
COUPON_WORDS = ("SPRING", "SUMMER", "AUTUMN", "WINTER", "WELCOME", "LOYAL", "FLASH", "BUNDLE", "FRIEND", "VIP")
CATEGORIES = (
    "Apparel", "Audio", "Bath", "Garden", "Kitchen", "Lighting", "Office", "Outdoor", "Stationery", "Storage",
    "Travel", "Wellness",
)  # fmt: skip
STATUSES = ("pending", "paid", "shipped", "delivered", "returned")
PAYMENT_METHODS = ("credit card", "debit card", "bank transfer", "PayPal", "gift card", "invoice")
SHIPPING_METHODS = ("standard", "express", "overnight", "pickup", "freight")
CURRENCIES = ("USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "SEK")
PRIORITIES = ("low", "normal", "high", "urgent")
CHANNELS = ("web", "mobile app", "phone", "marketplace", "in store")
CUSTOMER_SEGMENTS = ("consumer", "small business", "enterprise", "education", "government")
CARRIERS = ("Bluebird Post", "Northline Freight", "Swiftway", "Harbor Express", "Parcelwise", "Summit Cargo")

DATES = tuple(
    f"{year}-{month:02d}-{day:02d}"
    for year in (2023, 2024, 2025)
    for month, days in enumerate((31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31), start=1)
    for day in range(1, days + 1)
)

COMPANY: Space = (CAPITALIZED_WORDS, (" ",), COMPANY_SUFFIXES)
CITY: Space = (CITY_PREFIXES, CITY_SUFFIXES)
PERSON: Space = (FIRST_NAMES, (" ",), LAST_NAMES)
DECIMAL_TENTHS: Space = (numbers(1, 100), (".",), DIGITS)

ORDER_COLUMNS = (
    # Each round of 8 columns holds a key column, two small categories, two large categories, two numbers and a date,
    # so every table width has about the same mix of column kinds.
    ColumnSpec("order_id", (("ORD-",), NONZERO_DIGITS, *(DIGITS,) * 5), None),
    ColumnSpec("status", (STATUSES,), len(STATUSES)),
    ColumnSpec("shipping_city", CITY, 300),
    ColumnSpec("quantity", (numbers(1, 51),), 50),
    ColumnSpec("order_date", (DATES,), len(DATES)),
    ColumnSpec("payment_method", (PAYMENT_METHODS,), len(PAYMENT_METHODS)),
    ColumnSpec("product", (PRODUCT_ADJECTIVES, (" ",), PRODUCT_NOUNS), 400),
    ColumnSpec("unit_price", (numbers(1, 500), (".",), DIGITS, DIGITS), 2000),
    ColumnSpec("customer", (FIRST_NAMES, (" ",), UPPERCASE, (". ",), LAST_NAMES), None),
    ColumnSpec("category", (CATEGORIES,), len(CATEGORIES)),
    ColumnSpec("country", (COUNTRIES,), len(COUNTRIES)),
    ColumnSpec("total", (numbers(10, 10000), (".",), DIGITS, DIGITS), 3000),
    ColumnSpec("ship_date", (DATES,), len(DATES)),
    ColumnSpec("shipping_method", (SHIPPING_METHODS,), len(SHIPPING_METHODS)),
    ColumnSpec("sales_rep", PERSON, 60),
    ColumnSpec("discount_percent", (numbers(0, 41),), 41),
    ColumnSpec("email", (WORDS, DIGITS, DIGITS, DIGITS, ("@",), EMAIL_DOMAINS), None),
    ColumnSpec("warehouse", (("WH-",), DIGITS, NONZERO_DIGITS), 8),
    ColumnSpec("company", COMPANY, 300),
    ColumnSpec("tax", (numbers(0, 100), (".",), DIGITS, DIGITS), 2000),
    ColumnSpec("delivery_date", (DATES,), len(DATES)),
    ColumnSpec("currency", (CURRENCIES,), len(CURRENCIES)),
    ColumnSpec("sku", (("SKU-",), UPPERCASE, UPPERCASE, *(DIGITS,) * 4), 400),
    ColumnSpec("shipping_cost", (numbers(1, 50), (".",), DIGITS, DIGITS), 1000),
    ColumnSpec("tracking_number", (("1Z",), *(UPPERCASE,) * 2, *(DIGITS,) * 8), None),
    ColumnSpec("priority", (PRIORITIES,), len(PRIORITIES)),
    ColumnSpec("billing_city", CITY, 300),
    ColumnSpec("weight_kg", DECIMAL_TENTHS, 500),
    ColumnSpec("invoice_date", (DATES,), len(DATES)),
    ColumnSpec("channel", (CHANNELS,), len(CHANNELS)),
    ColumnSpec("shipping_address", (numbers(1, 1000), (" ",), CAPITALIZED_WORDS, (" ",), STREET_TYPES), 400),
    ColumnSpec("rating", (numbers(1, 6),), 5),
    ColumnSpec("invoice_number", (("INV-",), UPPERCASE, UPPERCASE, ("-",), *(DIGITS,) * 5), None),
    ColumnSpec("customer_segment", (CUSTOMER_SEGMENTS,), len(CUSTOMER_SEGMENTS)),
    ColumnSpec("supplier", COMPANY, 80),
    ColumnSpec("loyalty_points", (numbers(0, 10000),), 3000),
    ColumnSpec("due_date", (DATES,), len(DATES)),
    ColumnSpec("carrier", (CARRIERS,), len(CARRIERS)),
    ColumnSpec("coupon_code", (COUPON_WORDS, ("5", "10", "15", "20", "25")), 50),
    ColumnSpec("margin_percent", DECIMAL_TENTHS, 500),
)
