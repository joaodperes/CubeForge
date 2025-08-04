import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Load data
df = pd.read_csv("cube_stats.csv", sep=";", quotechar='"', encoding="utf-8")

# Convert comma decimals to float
numeric_cols = [
    "AmberControl", "ExpectedAmber", "ArtifactControl",
    "CreatureControl", "Efficiency", "Recursion"
]

for col in numeric_cols:
    df[col] = df[col].str.replace(",", ".").astype(float)

# Group by House
grouped = df.groupby("House").agg(
    UniqueCards=("CardTitle", "nunique"),
    AvgAmberControl=("AmberControl", "mean"),
    AvgExpectedAmber=("ExpectedAmber", "mean"),
    AvgArtifactControl=("ArtifactControl", "mean"),
    AvgCreatureControl=("CreatureControl", "mean"),
    AvgEfficiency=("Efficiency", "mean"),
    AvgRecursion=("Recursion", "mean")
).reset_index()

# Chart definitions
plot_info = [
    ("UniqueCards", "Number of Unique Cards per House"),
    ("AvgAmberControl", "Average Amber Control per House"),
    ("AvgExpectedAmber", "Average Expected Amber per House"),
    ("AvgArtifactControl", "Average Artifact Control per House"),
    ("AvgCreatureControl", "Average Creature Control per House"),
    ("AvgEfficiency", "Average Efficiency per House"),
    ("AvgRecursion", "Average Recursion per House"),
]

# Output charts
sns.set(style="whitegrid")
for column, title in plot_info:
    plt.figure(figsize=(10, 6))
    sns.barplot(data=grouped, x="House", y=column, palette="viridis")
    plt.title(title)
    plt.xlabel("House")
    plt.ylabel("")
    plt.xticks(rotation=45)
    output_file = f"{column}.png"
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    print(f"Saved: {output_file}")