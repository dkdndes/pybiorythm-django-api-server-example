"""
Django management command to load biorhythm data using PyBiorythm library.

This command demonstrates how to:
1. Use PyBiorythm library to generate biorhythm calculations
2. Store the results in Django models/SQLite database
3. Handle data import and processing in batches
4. Provide progress feedback and error handling

Usage:
    python manage.py load_biorhythm_data --name "John Doe" --birthdate 1990-05-15 --days 365
    python manage.py load_biorhythm_data --name "Jane Smith" --birthdate 1985-03-22 \
        --days 730 --target-date 2024-01-01
"""

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from biorhythm_data.models import BiorhythmCalculation, BiorhythmData, Person

# Import PyBiorythm
try:
    from biorythm import BiorhythmCalculator

    BIORYTHM_AVAILABLE = True
except ImportError:
    BIORYTHM_AVAILABLE = False


class Command(BaseCommand):
    help = "Load biorhythm data for a person using PyBiorythm library"

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str, required=True, help="Name of the person")
        parser.add_argument(
            "--birthdate", type=str, required=True, help="Birth date in YYYY-MM-DD format"
        )
        parser.add_argument(
            "--days", type=int, default=365, help="Number of days to calculate (default: 365)"
        )
        parser.add_argument(
            "--target-date",
            type=str,
            default=None,
            help="Target date for calculation start (default: today). Format: YYYY-MM-DD",
        )
        parser.add_argument("--email", type=str, default=None, help="Optional email address")
        parser.add_argument(
            "--notes", type=str, default="", help="Optional notes about this person"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for database inserts (default: 100)",
        )
        parser.add_argument(
            "--force", action="store_true", help="Force overwrite if person already exists"
        )

    def handle(self, *args, **options):
        if not BIORYTHM_AVAILABLE:
            raise CommandError(
                "PyBiorythm library is not available. "
                "Please install it: pip install git+https://github.com/dkdndes/pybiorythm.git"
            )

        # Parse and validate inputs
        try:
            birthdate = datetime.strptime(options["birthdate"], "%Y-%m-%d").date()
        except ValueError as err:
            raise CommandError(
                f"Invalid birthdate format: {options['birthdate']}. Use YYYY-MM-DD"
            ) from err

        target_date = None
        if options["target_date"]:
            try:
                target_date = datetime.strptime(options["target_date"], "%Y-%m-%d").date()
            except ValueError as err:
                raise CommandError(
                    f"Invalid target date format: {options['target_date']}. Use YYYY-MM-DD"
                ) from err
        else:
            target_date = date.today()

        if birthdate >= target_date:
            raise CommandError("Birth date must be before target date")

        days = options["days"]
        if days < 1 or days > 3650:  # Max ~10 years
            raise CommandError("Days must be between 1 and 3650")

        name = options["name"]
        batch_size = options["batch_size"]

        self.stdout.write(f"Loading biorhythm data for: {name}")
        self.stdout.write(f"Birth date: {birthdate}")
        self.stdout.write(f"Target date: {target_date}")
        self.stdout.write(f"Days to calculate: {days}")

        # Check if person already exists
        try:
            person = Person.objects.get(name=name, birthdate=birthdate)
            if not options["force"]:
                raise CommandError(
                    f"Person '{name}' with birthdate {birthdate} already exists. "
                    "Use --force to overwrite."
                )
            else:
                self.stdout.write("Person exists, will update data (--force specified)")
        except Person.DoesNotExist:
            person = None

        try:
            with transaction.atomic():
                # Create or update person
                if person:
                    person.email = options["email"] or person.email
                    person.notes = options["notes"] or person.notes
                    person.save()
                else:
                    person = Person.objects.create(
                        name=name,
                        birthdate=birthdate,
                        email=options["email"],
                        notes=options["notes"],
                    )

                self.stdout.write(f"✅ Person record: {person}")

                # Generate biorhythm data using PyBiorythm
                self.stdout.write("🔄 Generating biorhythm data with PyBiorythm...")

                calc = BiorhythmCalculator(days=days)
                birthdate_dt = datetime.combine(birthdate, datetime.min.time())
                target_date_dt = datetime.combine(target_date, datetime.min.time())

                biorhythm_json = calc.generate_timeseries_json(birthdate_dt, target_date_dt)

                # Create calculation record
                start_date = datetime.strptime(biorhythm_json["data"][0]["date"], "%Y-%m-%d").date()
                end_date = datetime.strptime(biorhythm_json["data"][-1]["date"], "%Y-%m-%d").date()

                calculation = BiorhythmCalculation.objects.create(
                    person=person,
                    start_date=start_date,
                    end_date=end_date,
                    days_calculated=len(biorhythm_json["data"]),
                    target_date=target_date,
                    pybiorythm_version=biorhythm_json.get("meta", {}).get("version", "unknown"),
                    notes=f"Generated via management command with {days} days",
                )

                self.stdout.write(f"✅ Calculation record: {calculation}")

                # Delete existing data for this person if force is specified
                if options["force"]:
                    deleted_count = BiorhythmData.objects.filter(person=person).delete()[0]
                    if deleted_count > 0:
                        self.stdout.write(f"🗑️  Deleted {deleted_count} existing data points")

                # Process biorhythm data in batches
                data_points = []
                total_points = len(biorhythm_json["data"])

                self.stdout.write(
                    f"📊 Processing {total_points} data points in batches of {batch_size}..."
                )

                for i, day_data in enumerate(biorhythm_json["data"]):
                    # Parse critical cycles
                    critical_cycles = day_data.get("critical_cycles", [])
                    is_physical_critical = "Physical" in critical_cycles
                    is_emotional_critical = "Emotional" in critical_cycles
                    is_intellectual_critical = "Intellectual" in critical_cycles

                    data_point = BiorhythmData(
                        person=person,
                        calculation=calculation,
                        date=datetime.strptime(day_data["date"], "%Y-%m-%d").date(),
                        days_alive=day_data["days_alive"],
                        physical=day_data["physical"],
                        emotional=day_data["emotional"],
                        intellectual=day_data["intellectual"],
                        is_physical_critical=is_physical_critical,
                        is_emotional_critical=is_emotional_critical,
                        is_intellectual_critical=is_intellectual_critical,
                    )
                    data_points.append(data_point)

                    # Insert batch when full
                    if len(data_points) >= batch_size:
                        BiorhythmData.objects.bulk_create(data_points)
                        self.stdout.write(
                            f"💾 Saved batch: {i + 1 - len(data_points) + 1}-{i + 1} of "
                            f"{total_points}"
                        )
                        data_points = []

                # Insert remaining data points
                if data_points:
                    BiorhythmData.objects.bulk_create(data_points)
                    self.stdout.write(
                        f"💾 Saved final batch: {total_points - len(data_points) + 1}-"
                        f"{total_points}"
                    )

                # Summary
                total_saved = BiorhythmData.objects.filter(person=person).count()
                critical_days = (
                    BiorhythmData.objects.filter(person=person)
                    .filter(
                        models.Q(is_physical_critical=True)
                        | models.Q(is_emotional_critical=True)
                        | models.Q(is_intellectual_critical=True)
                    )
                    .count()
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n🎉 Successfully loaded biorhythm data!\n"
                        f"   Person: {person.name}\n"
                        f"   Data points: {total_saved}\n"
                        f"   Date range: {start_date} to {end_date}\n"
                        f"   Critical days: {critical_days}\n"
                        f"   Database: SQLite ({calculation.id})"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error loading data: {str(e)}"))
            raise CommandError(f"Failed to load biorhythm data: {str(e)}") from e


# Django Q objects already imported above
