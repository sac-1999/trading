import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def trade_summary_with_plots(df):
    summary = {}
    summary["total_trades"] = len(df)
    df['netrr'] = np.where(df['maxrr']<1, -1, 
                           np.where(df['maxrr']>2, 2, df['rr']))
    print(df.head(50))

    summary["winning_trades"] = (df["netrr"] >= 0).sum()
    summary["losing_trades"] = (df["netrr"] < 0).sum()
    summary["breakeven_trades"] = (df["netrr"] == 0).sum()
    summary["winrate_%"] = round(summary["winning_trades"] / summary["total_trades"] * 100, 2)
    summary["avg_rr"] = round(df["netrr"].mean(), 2)
    summary["best_trade_rr"] = df["netrr"].max()
    summary["worst_trade_rr"] = df["netrr"].min()
    summary["net_rr"] = round(df["netrr"].sum(), 2)
    df["cum_rr"] = df["netrr"].cumsum()

    fig, axs = plt.subplots(3, 1, figsize=(10, 12))

    df["cum_rr"].plot(ax=axs[0], title="Cumulative RR", color="blue")
    axs[0].axhline(0, color="black", linestyle="--")

    df["netrr"].plot(kind="bar", ax=axs[1], title="Trade Results (RR)", color=df["netrr"].apply(lambda x: "green" if x > 0 else "red"))

    labels = ["Wins", "Losses", "Breakeven"]
    sizes = [summary["winning_trades"], summary["losing_trades"], summary["breakeven_trades"]]
    axs[2].pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=["green", "red", "gray"])
    axs[2].set_title("Win/Loss Distribution")

    plt.tight_layout()
    plt.show()

    return summary, df

if __name__ == "__main__":
    df = pd.read_csv('allresults.csv')
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    print(df)
    summary, df = trade_summary_with_plots(df)
    print(summary)
