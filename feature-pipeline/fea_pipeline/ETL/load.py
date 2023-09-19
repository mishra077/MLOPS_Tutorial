import hopsworks
import pandas as pd
from great_expectations.core import ExpectationSuite
from hsfs.feature_group import FeatureGroup


from feature_pipeline.settings import SETTINGS

def to_feature_store(
        df: pd.DataFrame,
        validation_expectation_suite: ExpectationSuite,
        feature_group_version: int,
) -> FeatureGroup:
    """
    This defination is used to validate the data and load it to the feature store
    """

    # Connection to feature store

    connect = hopsworks.login(api_key_value=SETTINGS["FS_API_KEY"], project=SETTINGS["FS_PROJECT_NAME"])
    feat_store = connect.get_feature_store()

    # Create feature group

    feature_group = feat_store.get_or_create_feature_group(
        name = "energy_consumption",
        version = feature_group_version,
        description = "Hourly Energy Consumption in Denmark. Data is lagged by 15 days.",
        primary_key = ["area", "consumer_type"],
        event_time = "datetime-utc",
        online_enabled = True,
        expectation_suite = validation_expectation_suite,
    )

    # Insertion of data into feature store

    feature_group.insert(
        feature = df,
        overwrite = False,
        write_options = {
            "wait_for_job": True,
        },
    )

    # Add feature descriptions.
    feature_descriptions = [
        {
            "name": "datetime_utc",
            "description": """
                            Datetime interval in UTC when the data was observed.
                            """,
            "validation_rules": "Always full hours, i.e. minutes are 00",
        },
        {
            "name": "area",
            "description": """
                            Denmark is divided in two price areas, divided by the Great Belt: DK1 and DK2.
                            If price area is “DK”, the data covers all Denmark.
                            """,
            "validation_rules": "0 (DK), 1 (DK1) or 2 (Dk2) (int)",
        },
        {
            "name": "consumer_type",
            "description": """
                            The consumer type is the Industry Code DE35 which is owned by Danish Energy. 
                            The code is used by Danish energy companies.
                            """,
            "validation_rules": ">0 (int)",
        },
        {
            "name": "energy_consumption",
            "description": "Total electricity consumption in kWh.",
            "validation_rules": ">=0 (float)",
        },
    ]

    for description in feature_descriptions:
        feature_group.update_feature_description(
            description["name"], description["description"]
        )
    
    # Update statistics.
    feature_group.statistics_config = {
        "enabled": True,
        "histograms": True,
        "correlations": True,
    }
    feature_group.update_statistics_config()
    feature_group.compute_statistics()

    return feature_group

