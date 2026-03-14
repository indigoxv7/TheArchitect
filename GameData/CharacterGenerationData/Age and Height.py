def generate_age(min_age, max_age, rng=None):
    import random

    if min_age > max_age:
        raise ValueError("min_age cannot be greater than max_age")
    if min_age < 0 or max_age > 100:
        raise ValueError("age range must stay between 0 and 100")

    population_by_age_bucket_millions = [
        (0, 10, 42.9),
        (11, 20, 43.6),
        (21, 30, 45.0),
        (31, 40, 47.0),
        (41, 50, 42.1),
        (51, 60, 41.2),
        (61, 70, 40.0),
        (71, 80, 26.2),
        (81, 90, 10.0),
        (91, 100, 2.0),
    ]

    candidate_ages = []
    candidate_weights = []

    for bucket_start_age, bucket_end_age, bucket_population_millions in population_by_age_bucket_millions:
        overlap_start_age = max(min_age, bucket_start_age)
        overlap_end_age = min(max_age, bucket_end_age)

        if overlap_start_age > overlap_end_age:
            continue

        years_in_bucket = bucket_end_age - bucket_start_age + 1
        weight_per_age = bucket_population_millions / years_in_bucket

        for age in range(overlap_start_age, overlap_end_age + 1):
            candidate_ages.append(age)
            candidate_weights.append(weight_per_age)

    if not candidate_ages:
        raise ValueError("no valid ages available in the requested range")

    random_generator = rng if rng is not None else random
    return random_generator.choices(candidate_ages, weights=candidate_weights, k=1)[0]


def generate_height_inches(sex, rng=None):
    import random

    normalized_sex = sex.strip().lower()

    if normalized_sex == "male":
        mean_height_inches = 69.2
        standard_deviation_inches = 2.94
        minimum_height_inches = 60.0
        maximum_height_inches = 80.0
    elif normalized_sex == "female":
        mean_height_inches = 63.6
        standard_deviation_inches = 2.83
        minimum_height_inches = 55.0
        maximum_height_inches = 75.0
    else:
        raise ValueError("sex must be 'male' or 'female'")

    random_generator = rng if rng is not None else random

    while True:
        sampled_height_inches = random_generator.gauss(
            mean_height_inches,
            standard_deviation_inches,
        )

        if minimum_height_inches <= sampled_height_inches <= maximum_height_inches:
            return round(sampled_height_inches, 1)