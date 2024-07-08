import json
import sys
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from statistics import mean
from typing import Literal
from zipfile import ZipFile

import requests
import requests_cache
from prettytable import PrettyTable

requests_cache.install_cache("city_comparator")

HTTP_TIMEOUT = 10


class CityError(Exception):
    """Raised when something went wrong with the geocoding API or its computation."""


class ClimateError(Exception):
    """Raised when something went wrong with the climate API or its computation."""


class AirQualityError(Exception):
    """Raised when something went wrong with the air quality API or its computation."""


class NaturalDisasterError(Exception):
    """Raised when something went wrong with processing of the GASPAR database."""


@dataclass(frozen=True)
class City:
    name: str
    latitude: float
    longitude: float
    elevation: int
    population: int
    region: str


@dataclass(frozen=True)
class AirQuality:
    european_aqi_min: int
    european_aqi_pm2_5_min: int
    european_aqi_pm10_min: int
    european_aqi_nitrogen_dioxide_min: int
    european_aqi_ozone_min: int
    european_aqi_sulphur_dioxide_min: int

    european_aqi_max: int
    european_aqi_pm2_5_max: int
    european_aqi_pm10_max: int
    european_aqi_nitrogen_dioxide_max: int
    european_aqi_ozone_max: int
    european_aqi_sulphur_dioxide_max: int

    european_aqi_mean: float
    european_aqi_pm2_5_mean: float
    european_aqi_pm10_mean: float
    european_aqi_nitrogen_dioxide_mean: float
    european_aqi_ozone_mean: float
    european_aqi_sulphur_dioxide_mean: float


@dataclass(frozen=True)
class DailyWeather:
    """The weather in a given city on a given day."""

    # The day on which this weather occurred.
    date: date

    # Maximum air temperature at 2 meters above ground.
    temperature_2m_max: float

    # Minimum air temperature at 2 meters above ground.
    temperature_2m_min: float

    # Mean temperature during the day, 2 meters above the ground.
    temperature_2m_mean: float

    # Maximum wind speed on a day.
    wind_speed_10m_max: float

    # Number of seconds of daylight per day.
    daylight_duration: float

    # The number of seconds of sunshine per day is determined by calculating direct
    # normalized irradiance exceeding 120 W/m², following the WMO definition.
    # Sunshine duration will consistently be less than daylight duration due to dawn and
    # dusk.
    sunshine_duration: float

    # Sum of daily rain.
    rain_sum: float

    # Sum of daily snowfall.
    snowfall_sum: float

    # The number of hours with rain.
    precipitation_hours: float

    # Evapotranspiration of a well watered grass field.
    # Commonly used to estimate the required irrigation for plants.
    et0_fao_evapotranspiration: float


@dataclass(frozen=True)
class SeasonWeatherMean:
    """The weather in a given city for a given year and season."""

    # The season for which this weather occurred.
    season: Literal["summer", "winter"]

    # Mean of the maximum air temperature at 2 meters above ground
    # over a given period of time.
    temperature_2m_max_mean: float

    # Mean of the minimum air temperature at 2 meters above ground
    # over a given period of time.
    temperature_2m_min_mean: float

    # Mean temperature 2 meters above the ground over a given period of time.
    temperature_2m_mean: float

    # Mean of maximum wind speed on a day over a given period of time.
    wind_speed_10m_max_mean: float

    # Mean of the number of seconds of daylight per day over a given period of time.
    daylight_duration_mean: float

    # Mean of the number of seconds of sunshine per day over a given period of time.
    sunshine_duration_mean: float

    # Mean of the sum of daily rain over a given period of time.
    rain_sum_mean: float

    # Mean of the sum of daily snowfall over a given period of time.
    snowfall_sum_mean: float

    # Mean of the number of hours with rain over a given period of time.
    precipitation_hours_mean: float

    # Mean of the evapotranspiration of a well watered grass field.
    # Commonly used to estimate the required irrigation for plants.
    et0_fao_evapotranspiration_mean: float


def get_weather(city: City, start_date: date, end_date: date) -> list[DailyWeather]:
    resp = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": city.latitude,
            "longitude": city.longitude,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "apparent_temperature_max",
                "daylight_duration",
                "sunshine_duration",
                "wind_speed_10m_max",
                "rain_sum",
                "snowfall_sum",
                "precipitation_hours",
                "et0_fao_evapotranspiration",
            ],
        },
        timeout=HTTP_TIMEOUT,
    )

    json_content = resp.json()

    if resp.status_code != 200:
        raise ClimateError(json_content["reason"])

    json_content = json_content["daily"]

    time = json_content["time"]
    temperature_2m_max = json_content["temperature_2m_max"]
    temperature_2m_min = json_content["temperature_2m_min"]
    temperature_2m_mean = json_content["temperature_2m_mean"]
    daylight_duration = json_content["daylight_duration"]
    sunshine_duration = json_content["sunshine_duration"]
    wind_speed_10m_max = json_content["wind_speed_10m_max"]
    rain_sum = json_content["rain_sum"]
    snowfall_sum = json_content["snowfall_sum"]
    precipitation_hours = json_content["precipitation_hours"]
    et0_fao_evapotranspiration = json_content["et0_fao_evapotranspiration"]

    measurements = []
    for i in range(len(time)):
        year, month, day = time[i].split("-")
        year, month, day = int(year), int(month), int(day)
        dw = DailyWeather(
            date(year, month, day),
            temperature_2m_max[i],
            temperature_2m_min[i],
            temperature_2m_mean[i],
            wind_speed_10m_max[i],
            daylight_duration[i],
            sunshine_duration[i],
            rain_sum[i],
            snowfall_sum[i],
            precipitation_hours[i],
            et0_fao_evapotranspiration[i],
        )
        measurements.append(dw)
    return measurements


def process_season_weather_mean(
    weather_measurements: list[DailyWeather],
) -> tuple[SeasonWeatherMean, SeasonWeatherMean]:
    """Process winter and summer means given all the input measurements.

    Winter is considered to last over december, january and february.
    Summer is considered to last over june, july and august.
    """
    years_to_process = {wm.date.year for wm in weather_measurements}

    winter_temperature_2m_max_values = []
    winter_temperature_2m_min_values = []
    winter_temperature_2m_values = []
    winter_wind_speed_10m_max_values = []
    winter_daylight_duration_values = []
    winter_sunshine_duration_values = []
    winter_rain_sum_values = []
    winter_snowfall_sum_values = []
    winter_precipitation_hours_values = []
    winter_et0_fao_evapotranspiration_values = []

    summer_temperature_2m_max_values = []
    summer_temperature_2m_min_values = []
    summer_temperature_2m_values = []
    summer_wind_speed_10m_max_values = []
    summer_daylight_duration_values = []
    summer_sunshine_duration_values = []
    summer_rain_sum_values = []
    summer_snowfall_sum_values = []
    summer_precipitation_hours_values = []
    summer_et0_fao_evapotranspiration_values = []

    # We process measurements per year in order to validate the dataset and
    # ensure there will be no bias in the results.
    for year in years_to_process:
        weather_measurements_for_the_given_year = [
            wm for wm in weather_measurements if wm.date.year == year
        ]
        weather_measurements_in_december = [
            wm for wm in weather_measurements_for_the_given_year if wm.date.month == 12
        ]
        weather_measurements_in_january = [
            wm for wm in weather_measurements_for_the_given_year if wm.date.month == 1
        ]
        weather_measurements_in_february = [
            wm for wm in weather_measurements_for_the_given_year if wm.date.month == 2
        ]
        weather_measurements_in_june = [
            wm for wm in weather_measurements_for_the_given_year if wm.date.month == 6
        ]
        weather_measurements_in_july = [
            wm for wm in weather_measurements_for_the_given_year if wm.date.month == 7
        ]
        weather_measurements_in_august = [
            wm for wm in weather_measurements_for_the_given_year if wm.date.month == 8
        ]

        if len(weather_measurements_in_december) != 31:
            error = (
                "missing weather measurements for december, got only "
                f"{len(weather_measurements_in_december)} measures instead of 31"
            )
            raise ClimateError(error)

        if len(weather_measurements_in_january) != 31:
            error = (
                "missing weather measurements for january, got only "
                f"{len(weather_measurements_in_january)} measures instead of 31"
            )
            raise ClimateError(error)

        if len(weather_measurements_in_february) not in (28, 29):
            error = (
                "missing weather measurements for february, got only "
                f"{len(weather_measurements_in_february)} measures instead of 28 or 29"
            )
            raise ClimateError(error)

        if len(weather_measurements_in_june) != 30:
            error = (
                "missing weather measurements for june, got only "
                f"{len(weather_measurements_in_june)} measures instead of 31"
            )
            raise ClimateError(error)

        if len(weather_measurements_in_july) != 31:
            error = (
                "missing weather measurements for july, got only "
                f"{len(weather_measurements_in_july)} measures instead of 31"
            )
            raise ClimateError(error)

        if len(weather_measurements_in_august) != 31:
            error = (
                "missing weather measurements for august, got only "
                f"{len(weather_measurements_in_august)} measures instead of 31"
            )
            raise ClimateError(error)

        winter_measurements_to_process = (
            weather_measurements_in_december
            + weather_measurements_in_january
            + weather_measurements_in_february
        )

        summer_measurements_to_process = (
            weather_measurements_in_june
            + weather_measurements_in_july
            + weather_measurements_in_august
        )

        for weather_measurement in winter_measurements_to_process:
            winter_temperature_2m_max_values.append(
                weather_measurement.temperature_2m_max
            )
            winter_temperature_2m_min_values.append(
                weather_measurement.temperature_2m_min
            )
            winter_temperature_2m_values.append(weather_measurement.temperature_2m_mean)
            winter_wind_speed_10m_max_values.append(
                weather_measurement.wind_speed_10m_max
            )
            winter_daylight_duration_values.append(
                weather_measurement.daylight_duration
            )
            winter_sunshine_duration_values.append(
                weather_measurement.sunshine_duration
            )
            winter_rain_sum_values.append(weather_measurement.rain_sum)
            winter_snowfall_sum_values.append(weather_measurement.snowfall_sum)
            winter_precipitation_hours_values.append(
                weather_measurement.precipitation_hours
            )
            winter_et0_fao_evapotranspiration_values.append(
                weather_measurement.et0_fao_evapotranspiration
            )

        for weather_measurement in summer_measurements_to_process:
            summer_temperature_2m_max_values.append(
                weather_measurement.temperature_2m_max
            )
            summer_temperature_2m_min_values.append(
                weather_measurement.temperature_2m_min
            )
            summer_temperature_2m_values.append(weather_measurement.temperature_2m_mean)
            summer_wind_speed_10m_max_values.append(
                weather_measurement.wind_speed_10m_max
            )
            summer_daylight_duration_values.append(
                weather_measurement.daylight_duration
            )
            summer_sunshine_duration_values.append(
                weather_measurement.sunshine_duration
            )
            summer_rain_sum_values.append(weather_measurement.rain_sum)
            summer_snowfall_sum_values.append(weather_measurement.snowfall_sum)
            summer_precipitation_hours_values.append(
                weather_measurement.precipitation_hours
            )
            summer_et0_fao_evapotranspiration_values.append(
                weather_measurement.et0_fao_evapotranspiration
            )

    return (
        SeasonWeatherMean(
            "winter",
            temperature_2m_max_mean=mean(winter_temperature_2m_max_values),
            temperature_2m_min_mean=mean(winter_temperature_2m_min_values),
            temperature_2m_mean=mean(winter_temperature_2m_values),
            wind_speed_10m_max_mean=mean(winter_wind_speed_10m_max_values),
            daylight_duration_mean=mean(winter_daylight_duration_values),
            sunshine_duration_mean=mean(winter_sunshine_duration_values),
            rain_sum_mean=mean(winter_rain_sum_values),
            snowfall_sum_mean=mean(winter_snowfall_sum_values),
            precipitation_hours_mean=mean(winter_precipitation_hours_values),
            et0_fao_evapotranspiration_mean=mean(
                winter_et0_fao_evapotranspiration_values
            ),
        ),
        SeasonWeatherMean(
            "summer",
            temperature_2m_max_mean=mean(summer_temperature_2m_max_values),
            temperature_2m_min_mean=mean(summer_temperature_2m_min_values),
            temperature_2m_mean=mean(summer_temperature_2m_values),
            wind_speed_10m_max_mean=mean(summer_wind_speed_10m_max_values),
            daylight_duration_mean=mean(summer_daylight_duration_values),
            sunshine_duration_mean=mean(summer_sunshine_duration_values),
            rain_sum_mean=mean(summer_rain_sum_values),
            snowfall_sum_mean=mean(summer_snowfall_sum_values),
            precipitation_hours_mean=mean(summer_precipitation_hours_values),
            et0_fao_evapotranspiration_mean=mean(
                summer_et0_fao_evapotranspiration_values
            ),
        ),
    )


def get_air_quality_mean(city: City, start_date: date, end_date: date) -> AirQuality:
    resp = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude": city.latitude,
            "longitude": city.longitude,
            "hourly": [
                "european_aqi,european_aqi_pm2_5",
                "european_aqi_pm10",
                "european_aqi_nitrogen_dioxide",
                "european_aqi_ozone",
                "european_aqi_sulphur_dioxide",
            ],
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
        timeout=HTTP_TIMEOUT,
    )

    json_content = resp.json()

    if resp.status_code != 200:
        raise AirQualityError(json_content["reason"])

    json_content = json_content["hourly"]

    european_aqi = [v for v in json_content["european_aqi"] if v is not None]
    european_aqi_pm2_5 = [
        v for v in json_content["european_aqi_pm2_5"] if v is not None
    ]
    european_aqi_pm10 = [v for v in json_content["european_aqi_pm10"] if v is not None]
    european_aqi_nitrogen_dioxide = [
        v for v in json_content["european_aqi_nitrogen_dioxide"] if v is not None
    ]
    european_aqi_ozone = [
        v for v in json_content["european_aqi_ozone"] if v is not None
    ]
    european_aqi_sulphur_dioxide = [
        v for v in json_content["european_aqi_sulphur_dioxide"] if v is not None
    ]

    return AirQuality(
        european_aqi_min=min(european_aqi),
        european_aqi_pm2_5_min=min(european_aqi_pm2_5),
        european_aqi_pm10_min=min(european_aqi_pm10),
        european_aqi_nitrogen_dioxide_min=min(european_aqi_nitrogen_dioxide),
        european_aqi_ozone_min=min(european_aqi_ozone),
        european_aqi_sulphur_dioxide_min=min(european_aqi_sulphur_dioxide),
        european_aqi_max=max(european_aqi),
        european_aqi_pm2_5_max=max(european_aqi_pm2_5),
        european_aqi_pm10_max=max(european_aqi_pm10),
        european_aqi_nitrogen_dioxide_max=max(european_aqi_nitrogen_dioxide),
        european_aqi_ozone_max=max(european_aqi_ozone),
        european_aqi_sulphur_dioxide_max=max(european_aqi_sulphur_dioxide),
        european_aqi_mean=mean(european_aqi),
        european_aqi_pm2_5_mean=mean(european_aqi_pm2_5),
        european_aqi_pm10_mean=mean(european_aqi_pm10),
        european_aqi_nitrogen_dioxide_mean=mean(european_aqi_nitrogen_dioxide),
        european_aqi_ozone_mean=mean(european_aqi_ozone),
        european_aqi_sulphur_dioxide_mean=mean(european_aqi_sulphur_dioxide),
    )


def get_referenced_natural_disaster_count(city: City) -> int:
    resp = requests.get(
        "http://files.georisques.fr/GASPAR/gaspar.zip",
        timeout=HTTP_TIMEOUT,
    )
    f = ZipFile(BytesIO(resp.content))

    natural_disasters_count = 0

    with f.open("catnat_gaspar.csv", "r") as csv:
        _ = csv.readline()  # Skip CSV header

        for line in csv:
            if f";{city.name};".encode() in line:
                natural_disasters_count += 1

    return natural_disasters_count


def get_soil_pollution_incidents_count(city: City) -> int:
    """Return how many pollution incidents happened in the given city.

    https://www.data.gouv.fr/en/datasets/base-des-sols-pollues/
    """

    incidents_count = 0
    with open("/home/shellcode/downloads/BASOL.json", "r") as basol_fd:
        basol_json = json.load(basol_fd)["sites"]

        for entry in basol_json:
            if entry["identification"]["commune"].lower() == city.name.lower():
                incidents_count += 1

    return incidents_count


def search_city(name: str) -> City:
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": name, "count": 10, "language": "fr", "format": "json"},
        timeout=HTTP_TIMEOUT,
    )

    json_content = resp.json()

    if resp.status_code != 200:
        raise ClimateError(json_content["reason"])

    results = [
        entry
        for entry in json_content["results"]
        if "country" in entry
        and entry["country"] == "France"
        and entry["feature_code"].startswith("PPL")
        and "population" in entry
    ]

    # Prioritize results which are exact matches
    if len(results) > 1:
        results = [r for r in results if r["name"] == name]

    if len(results) > 1:
        error = f"{len(results)} results were found for '{name}', don't know which one to pick"
        raise CityError(error)

    city = results[0]

    return City(
        city["name"],
        city["latitude"],
        city["longitude"],
        city["elevation"],
        city["population"],
        city["admin2"],
    )


def main(city_names: list[str]) -> None:
    cities = [search_city(name) for name in city_names]

    city_table = PrettyTable()
    city_table.align = "l"
    city_table.field_names = ["Nom", "Département", "Altitude (m)", "Population"]
    for city in cities:
        city_table.add_row(
            [city.name, city.region, int(city.elevation), city.population],
            divider=True,
        )

    metrics = [
        "Température moyenne (°C)",
        "Température journalière min moyenne (°C)",
        "Température journalière max moyenne (°C)",
        "Précipitations pluie (mm)",
        "Précipitations neige (mm)",
        "Vitesse du vent moyenne 10m au dessus du sol (km/h)",
        "Nombre d'heures d'ensolleillement par jour",
        "Nombre d'heures de pluie par jour (pas une durée mais une quantité)",
        "Nombre d'heures où il fait jour",
        "Evapotranspiration (mm)",
    ]

    winter_climat_table = PrettyTable()
    winter_climat_table.add_column(
        "Métrique",
        metrics,
        align="l",
    )

    for name in city_names:
        winter_climat_table.custom_format[name] = lambda _, v: f"{v:.2f}"

    summer_climat_table = PrettyTable()
    summer_climat_table.add_column(
        "Métrique",
        metrics,
        align="l",
    )

    for name in city_names:
        summer_climat_table.custom_format[name] = lambda _, v: f"{v:.2f}"

    for city in cities:
        weather = get_weather(city, date(2010, 1, 1), date(2023, 12, 31))
        winter_mean, summer_mean = process_season_weather_mean(weather)
        winter_climat_table.add_column(
            city.name,
            [
                winter_mean.temperature_2m_mean,
                winter_mean.temperature_2m_min_mean,
                winter_mean.temperature_2m_max_mean,
                winter_mean.rain_sum_mean,
                winter_mean.snowfall_sum_mean * 10,  # convert to mm
                winter_mean.wind_speed_10m_max_mean,
                winter_mean.sunshine_duration_mean / 3600,  # convert to hours
                winter_mean.precipitation_hours_mean,
                winter_mean.daylight_duration_mean / 3600,  # convert to hours
                winter_mean.et0_fao_evapotranspiration_mean,
            ],
            align="l",
        )

        summer_climat_table.add_column(
            city.name,
            [
                summer_mean.temperature_2m_mean,
                summer_mean.temperature_2m_min_mean,
                summer_mean.temperature_2m_max_mean,
                summer_mean.rain_sum_mean,
                summer_mean.snowfall_sum_mean * 10,  # convert to mm
                summer_mean.wind_speed_10m_max_mean,
                summer_mean.sunshine_duration_mean / 3600,  # convert to hours
                summer_mean.precipitation_hours_mean,
                summer_mean.daylight_duration_mean / 3600,  # convert to hours
                summer_mean.et0_fao_evapotranspiration_mean,
            ],
            align="l",
        )

    # Hack because we cannot use the regular API for dividers when using add_column
    winter_climat_table._dividers = [True] * len(metrics)
    summer_climat_table._dividers = [True] * len(metrics)

    metrics = [
        "Indice de qualité de l'air moyen",
        "Indice de qualité de l'air max (pics de pollution)",
        "Nombre de catastrophes naturelles recensées dans la base GASPAR",
        "Nombre d'incidents recensés dans la base BASOL ayants entrainé une pollution des sols",
    ]
    risks_table = PrettyTable()
    risks_table.add_column(
        "Métrique",
        metrics,
        align="l",
    )

    for city in cities:
        air_quality_mean = get_air_quality_mean(
            city,
            date(2022, 7, 29),
            date(2024, 7, 7),
        )
        natural_disasters_count = get_referenced_natural_disaster_count(city)
        soil_pollution_incidents_counts = get_soil_pollution_incidents_count(city)
        risks_table.add_column(
            city.name,
            [
                int(air_quality_mean.european_aqi_mean),
                air_quality_mean.european_aqi_max,
                natural_disasters_count,
                soil_pollution_incidents_counts,
            ],
        )

    # Hack because we cannot use the regular API for dividers when using add_column
    risks_table._dividers = [True] * len(metrics)

    print("Villes à l'étude:")
    print(city_table)
    print()
    print("Climat hivernal:")
    print(winter_climat_table)
    print()
    print("Climat estival:")
    print(summer_climat_table)
    print()
    print("Risques:")
    print(risks_table)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [CITY...]")
        sys.exit(1)
    main(sys.argv[1:])
