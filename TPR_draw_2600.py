import pandas as pd
import json
import os
import matplotlib.pyplot as plt

def calculate_stats_2600(file_path, fide_map):
    if not os.path.exists(file_path):
        print(f"File '{file_path}' not found.")
        return None

    df = pd.read_csv(file_path)

    df['Score'] = df['Score'].astype(float)
    df['Opponent Rating'] = pd.to_numeric(df['Opponent Rating'], errors='coerce')
    df = df.dropna(subset=['Opponent Rating'])
    df = df[df['Opponent Rating'] >= 2600]
    stats = []
    candidates = df['Candidate'].unique()

    for player in candidates:
        player_games = df[df['Candidate'] == player]
        
        total_games = len(player_games)
        if total_games == 0:
            continue
            
        total_score = player_games['Score'].sum()
        avg_opp_rating = player_games['Opponent Rating'].mean()
        score_pct = total_score / total_games
        
        pct_key = "{:.2f}".format(score_pct)
        if score_pct > 0.995: pct_key = "1.00"
        if score_pct < 0.005: pct_key = "0.00"
        
        dp = fide_map.get(pct_key, 0)
        tpr = avg_opp_rating + dp
        draws = len(player_games[player_games['Score'] == 0.5])
        draw_rate = (draws / total_games) * 100 
        
        stats.append({
            "Player": player,
            "Games": total_games,
            "Score": total_score,
            "Avg Opp Rating": round(avg_opp_rating, 1),
            "TPR": int(round(tpr)),
            "Draw Rate %": round(draw_rate, 1)
        })

    summary_df = pd.DataFrame(stats)
    
    if not summary_df.empty:
        summary_df = summary_df.sort_values(by="TPR", ascending=False)
    
        print(f"Classical Performance Table (>2600)")
        print(summary_df.to_string(index=False))
        
        output_filename = f"stats_classical_2600plus.csv"
        summary_df.to_csv(output_filename, index=False)
        print(f"Saved CSV to {output_filename}")
        
        fig, ax = plt.subplots(figsize=(10, len(summary_df) * 0.5 + 1.5))
        ax.axis('off')
        ax.axis('tight')

        table = ax.table(cellText=summary_df.values,
                         colLabels=summary_df.columns,
                         loc='center',
                         cellLoc='center')

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor('#4e79a7')
                cell.set_text_props(weight='bold', color='white')
                cell.set_linewidth(0)
            else:
                cell.set_linewidth(0)
                if row % 2 == 0:
                    cell.set_facecolor('#f2f2f2')

        plt.title("Classical Performance (>2600 Opponents)", weight='bold', pad=20)
        
        img_filename = "stats_classical_table.png"
        plt.savefig(img_filename, bbox_inches='tight', dpi=300)
        print(f"Saved Image to {img_filename}")
        plt.close()

with open("fide_table.json", "r") as f:
    fide_values = json.load(f)

calculate_stats_2600("candidates_classical_2024_2026.csv", fide_values)
