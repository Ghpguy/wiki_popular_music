
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency, ttest_ind, f_oneway, kruskal
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import dendrogram, linkage
import networkx as nx
import argparse
import os

def load_data(path):
    df = pd.read_csv(path)
    df["Top Ten Entry Date"] = pd.to_datetime(df["Top Ten Entry Date"], errors="coerce")
    df["Peak Date"] = pd.to_datetime(df["Peak Date"], errors="coerce")
    df["Weeks in Top Ten"] = pd.to_numeric(df["Weeks in Top Ten"], errors="coerce")
    df["Peak"] = pd.to_numeric(df["Peak"], errors="coerce")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Decade"] = (df["Year"] // 10) * 10
    df["Lag to Peak"] = (df["Peak Date"] - df["Top Ten Entry Date"]).dt.days
    return df

def peak_position_insights(df, save=False):
    print("=== Peak Position Insights ===")
    counts = df["Peak"].value_counts().sort_index()
    print("Counts by peak:\n", counts)
    counts.plot(kind="bar")
    plt.title("Songs by Peak Position")
    if save: plt.savefig("outputs/peak_counts.png")
    plt.show()

    conversion_rate = (df["Peak"] == 1).mean() * 100
    print(f"Conversion rate to #1: {conversion_rate:.2f}%")

    avg_weeks = df.groupby("Peak")["Weeks in Top Ten"].mean()
    print("Average weeks in Top Ten by Peak:\n", avg_weeks)
    avg_weeks.plot(kind="bar")
    plt.title("Avg Weeks by Peak Position")
    if save: plt.savefig("outputs/avg_weeks_peak.png")
    plt.show()

    df["Peak_bin"] = pd.cut(df["Peak"], bins=[0,1,3,5,10], labels=["1","2-3","4-5","6-10"])
    contingency = pd.crosstab(df["Peak_bin"], df["Decade"])
    chi2, p, _, _ = chi2_contingency(contingency)
    print(f"Chi-square test (peak vs decade): chi2={chi2:.2f}, p={p:.4f}")

    groups = [g["Weeks in Top Ten"].dropna() for _, g in df.groupby("Peak_bin")]
    for i in range(len(groups)):
        for j in range(i+1, len(groups)):
            t, p = ttest_ind(groups[i], groups[j], equal_var=False)
            print(f"T-test {df['Peak_bin'].cat.categories[i]} vs {df['Peak_bin'].cat.categories[j]}: t={t:.2f}, p={p:.4f}")

def yearly_trends(df, save=False):
    print("=== Yearly & Decadal Trends ===")
    entries_per_year = df.groupby("Year")["Single Name"].count()
    entries_per_year.plot()
    plt.title("Number of Top Ten Entries per Year")
    if save: plt.savefig("outputs/entries_per_year.png")
    plt.show()

    avg_per_year = df.groupby("Year")["Weeks in Top Ten"].mean()
    avg_per_year.plot()
    plt.title("Avg Weeks in Top Ten per Year")
    if save: plt.savefig("outputs/avg_per_year.png")
    plt.show()

    pct_num1 = df.groupby("Year").apply(lambda x: (x["Peak"]==1).mean()*100)
    pct_num1.plot()
    plt.title("% of Songs Reaching #1 per Year")
    if save: plt.savefig("outputs/pct_num1_per_year.png")
    plt.show()

    def era_map(y):
        if y <= 1999: return "Pre-digital"
        elif y <= 2014: return "Digital"
        else: return "Streaming"
    df["Era"] = df["Year"].apply(era_map)

    era_groups = [g["Weeks in Top Ten"].dropna() for _, g in df.groupby("Era")]
    f, p = f_oneway(*era_groups)
    print(f"ANOVA across eras: F={f:.2f}, p={p:.4f}")
    h, p = kruskal(*era_groups)
    print(f"Kruskal-Wallis across eras: H={h:.2f}, p={p:.4f}")

    df.groupby("Era")["Weeks in Top Ten"].mean().plot(kind="bar")
    plt.title("Avg Weeks in Top Ten by Era")
    if save: plt.savefig("outputs/avg_weeks_by_era.png")
    plt.show()

def seasonality(df, save=False):
    print("=== Seasonality ===")
    df["Month"] = df["Top Ten Entry Date"].dt.month
    month_counts = df["Month"].value_counts().sort_index()
    month_counts.plot(kind="bar")
    plt.title("Entries by Month")
    if save: plt.savefig("outputs/entries_by_month.png")
    plt.show()

    contingency = pd.crosstab(df["Month"], df["Decade"])
    chi2, p, _, _ = chi2_contingency(contingency)
    print(f"Chi-square test (month vs decade): chi2={chi2:.2f}, p={p:.4f}")

    df["Holiday"] = df["Month"].isin([11,12])
    holiday = df[df["Holiday"]]["Weeks in Top Ten"].dropna()
    non_holiday = df[~df["Holiday"]]["Weeks in Top Ten"].dropna()
    t, p = ttest_ind(holiday, non_holiday, equal_var=False)
    print(f"T-test (Holiday vs Non-Holiday longevity): t={t:.2f}, p={p:.4f}")

def clustering(df, k=3, save=False):
    print("=== Clustering Song Trajectories ===")
    features = df[["Lag to Peak", "Weeks in Top Ten", "Peak"]].dropna()
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(features)
    df.loc[features.index, "Cluster"] = km.labels_
    sns.scatterplot(x="Lag to Peak", y="Weeks in Top Ten", hue="Cluster", data=df)
    plt.title("K-means Clustering of Songs")
    if save: plt.savefig("outputs/kmeans_clusters.png")
    plt.show()

    subset = features.sample(min(150, len(features)), random_state=42)
    Z = linkage(subset, method="ward")
    plt.figure(figsize=(10,5))
    dendrogram(Z)
    plt.title("Hierarchical Clustering Dendrogram (subset)")
    if save: plt.savefig("outputs/hierarchical_dendrogram.png")
    plt.show()

def collaboration_network(df, save=False):
    print("=== Collaboration Network ===")
    G = nx.Graph()
    for artists in df["Artist(s)"].dropna():
        names = [a.strip() for a in str(artists).replace("feat.", ",").replace("&", ",").split(",") if a.strip()]
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                G.add_edge(names[i], names[j])
    deg = nx.degree_centrality(G)
    top = sorted(deg.items(), key=lambda x: x[1], reverse=True)[:10]
    print("Top artists by centrality:", top)
    plt.figure(figsize=(10,10))
    subG = G.subgraph(dict(top).keys())
    pos = nx.spring_layout(subG, seed=42)
    nx.draw(subG, pos, with_labels=True, node_size=1500, node_color="lightblue", font_size=10)
    plt.title("Top Artist Collaboration Subgraph")
    if save: plt.savefig("outputs/collab_network.png")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV dataset")
    parser.add_argument("--clusters", type=int, default=3, help="Number of k-means clusters")
    parser.add_argument("--save", action="store_true", help="Save plots to outputs/")
    args = parser.parse_args()

    if args.save and not os.path.exists("outputs"):
        os.makedirs("outputs")

    df = load_data(args.csv)
    peak_position_insights(df, save=args.save)
    yearly_trends(df, save=args.save)
    seasonality(df, save=args.save)
    clustering(df, k=args.clusters, save=args.save)
    collaboration_network(df, save=args.save)
