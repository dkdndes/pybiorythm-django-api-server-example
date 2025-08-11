from datetime import date

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Person(models.Model):
    """
    Represents a person with their biorhythm data.
    Stores basic information needed for biorhythm calculations.
    """

    name = models.CharField(max_length=200, help_text="Person's name or identifier")
    birthdate = models.DateField(help_text="Birth date for biorhythm calculations")
    email = models.EmailField(blank=True, null=True, help_text="Optional contact email")
    notes = models.TextField(blank=True, help_text="Optional notes about this person")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Person"
        verbose_name_plural = "People"

    def __str__(self):
        return f"{self.name} (born {self.birthdate})"

    @property
    def age_in_days(self):
        """Calculate current age in days."""
        return (date.today() - self.birthdate).days

    def get_biorhythm_data_count(self):
        """Get count of stored biorhythm data points."""
        return self.biorhythm_entries.count()


class BiorhythmCalculation(models.Model):
    """
    Stores metadata about biorhythm calculation requests.
    Tracks when calculations were performed and parameters used.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="calculations")
    start_date = models.DateField(help_text="Start date for calculation period")
    end_date = models.DateField(help_text="End date for calculation period")
    days_calculated = models.PositiveIntegerField(help_text="Number of days calculated")
    calculation_date = models.DateTimeField(
        auto_now_add=True, help_text="When this calculation was performed"
    )
    target_date = models.DateField(help_text="Target date used as calculation reference")
    pybiorythm_version = models.CharField(
        max_length=50, blank=True, help_text="PyBiorythm library version used"
    )
    notes = models.TextField(blank=True, help_text="Notes about this calculation")

    class Meta:
        ordering = ["-calculation_date"]
        verbose_name = "Biorhythm Calculation"
        verbose_name_plural = "Biorhythm Calculations"

    def __str__(self):
        return (
            f"{self.person.name}: {self.start_date} to {self.end_date} "
            f"({self.days_calculated} days)"
        )

    @property
    def date_range_str(self):
        """Human readable date range."""
        return f"{self.start_date} to {self.end_date}"


class BiorhythmData(models.Model):
    """
    Stores individual daily biorhythm data points.
    Each record represents one day's biorhythm values for a person.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="biorhythm_entries")
    calculation = models.ForeignKey(
        BiorhythmCalculation,
        on_delete=models.CASCADE,
        related_name="data_points",
        null=True,
        blank=True,
    )
    date = models.DateField(help_text="Date for this biorhythm reading")
    days_alive = models.PositiveIntegerField(help_text="Number of days since birth")

    # Biorhythm cycle values (-1.0 to 1.0)
    physical = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Physical cycle value (-1.0 to 1.0)",
    )
    emotional = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Emotional cycle value (-1.0 to 1.0)",
    )
    intellectual = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Intellectual cycle value (-1.0 to 1.0)",
    )

    # Critical day indicators
    is_physical_critical = models.BooleanField(
        default=False, help_text="Physical cycle near zero crossing"
    )
    is_emotional_critical = models.BooleanField(
        default=False, help_text="Emotional cycle near zero crossing"
    )
    is_intellectual_critical = models.BooleanField(
        default=False, help_text="Intellectual cycle near zero crossing"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["person", "date"]
        unique_together = ["person", "date"]  # One record per person per day
        verbose_name = "Biorhythm Data Point"
        verbose_name_plural = "Biorhythm Data Points"
        indexes = [
            models.Index(fields=["person", "date"]),
            models.Index(fields=["date"]),
            models.Index(fields=["days_alive"]),
            models.Index(
                fields=["is_physical_critical", "is_emotional_critical", "is_intellectual_critical"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.person.name} - {self.date}: P={self.physical:.3f}, "
            f"E={self.emotional:.3f}, I={self.intellectual:.3f}"
        )

    @property
    def is_any_critical(self):
        """Check if any cycle is in critical phase."""
        return (
            self.is_physical_critical or self.is_emotional_critical or self.is_intellectual_critical
        )

    @property
    def critical_cycles(self):
        """Get list of cycles that are in critical phase."""
        critical = []
        if self.is_physical_critical:
            critical.append("Physical")
        if self.is_emotional_critical:
            critical.append("Emotional")
        if self.is_intellectual_critical:
            critical.append("Intellectual")
        return critical

    @property
    def cycle_summary(self):
        """Get summary of all cycle values."""
        return {
            "physical": self.physical,
            "emotional": self.emotional,
            "intellectual": self.intellectual,
            "critical_cycles": self.critical_cycles,
        }


class BiorhythmAnalysis(models.Model):
    """
    Stores results of statistical analysis performed on biorhythm data.
    Useful for caching analysis results and tracking insights.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="analyses")
    analysis_type = models.CharField(
        max_length=50,
        choices=[
            ("correlation", "Correlation Analysis"),
            ("trend", "Trend Analysis"),
            ("statistical_summary", "Statistical Summary"),
            ("pattern_detection", "Pattern Detection"),
            ("critical_day_analysis", "Critical Day Analysis"),
        ],
        help_text="Type of analysis performed",
    )
    start_date = models.DateField(help_text="Start date of analyzed period")
    end_date = models.DateField(help_text="End date of analyzed period")
    analysis_date = models.DateTimeField(auto_now_add=True, help_text="When analysis was performed")

    # Results stored as JSON
    results = models.JSONField(help_text="Analysis results in JSON format")
    summary = models.TextField(help_text="Human-readable summary of results")

    # Analysis metadata
    data_points_analyzed = models.PositiveIntegerField(
        help_text="Number of data points included in analysis"
    )
    analysis_parameters = models.JSONField(default=dict, help_text="Parameters used for analysis")

    class Meta:
        ordering = ["-analysis_date"]
        verbose_name = "Biorhythm Analysis"
        verbose_name_plural = "Biorhythm Analyses"

    def __str__(self):
        return f"{self.person.name}: {self.analysis_type} ({self.start_date} to {self.end_date})"
