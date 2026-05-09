import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# 논문용 전역 폰트 및 스타일 설정
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'legend.fontsize': 12,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'lines.linewidth': 2,
    'lines.markersize': 8,
    'figure.autolayout': True
})

def load_data():
    file = 'fota_results.csv'
    if not os.path.exists(file):
        print(f"No CSV file found: {file}")
        return None
        
    try:
        merged_df = pd.read_csv(file)
        # 통계 처리를 위해 숫자로 변환
        merged_df['total_time_sec'] = pd.to_numeric(merged_df['total_time_sec'], errors='coerce')
        merged_df['loss_rate_pct'] = pd.to_numeric(merged_df['loss_rate_pct'], errors='coerce')
        merged_df['fw_size_bytes'] = pd.to_numeric(merged_df['fw_size_bytes'], errors='coerce')
        merged_df['overhead_pct'] = pd.to_numeric(merged_df['overhead_pct'], errors='coerce')
        
        # 결측치(FAIL 등) 제외
        merged_df = merged_df.dropna(subset=['total_time_sec'])
        return merged_df
    except Exception as e:
        print(f"Error reading {file}: {e}")
        return None

def plot_time_vs_loss(df, target_size=524288, label_size="512KB"):
    sub_df = df[df['fw_size_bytes'] == target_size]
    if sub_df.empty:
        return
        
    grouped = sub_df.groupby(['protocol', 'loss_rate_pct'])['total_time_sec'].mean().reset_index()
    
    plt.figure(figsize=(8, 6))
    protocols = grouped['protocol'].unique()
    markers = ['o', 's', '^', 'D']
    colors = ['#1f77b4', '#d62728', '#2ca02c']
    
    for i, proto in enumerate(protocols):
        proto_data = grouped[grouped['protocol'] == proto].sort_values('loss_rate_pct')
        plt.plot(proto_data['loss_rate_pct'], proto_data['total_time_sec'], 
                 marker=markers[i%len(markers)], color=colors[i%len(colors)],
                 linestyle='-' if 'Custom' in proto else '--',
                 label=proto)
                 
    plt.title(f'FOTA Update Time vs. Packet Error Rate ({label_size})')
    plt.xlabel('Packet Error Rate (%)')
    plt.ylabel('FOTA Update Time (s)')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(loc='best')
    
    plt.savefig(f'fig1_time_vs_loss_{label_size}.png', dpi=300)
    plt.close()
    print(f"Saved fig1_time_vs_loss_{label_size}.png")

def plot_time_vs_size(df, target_loss=0.01):
    sub_df = df[np.isclose(df['loss_rate_pct'], target_loss)]
    if sub_df.empty:
        target_loss = df['loss_rate_pct'].max()
        sub_df = df[df['loss_rate_pct'] == target_loss]
        if sub_df.empty: return
        
    grouped = sub_df.groupby(['protocol', 'fw_size_bytes'])['total_time_sec'].mean().reset_index()
    
    plt.figure(figsize=(8, 6))
    protocols = grouped['protocol'].unique()
    markers = ['o', 's', '^']
    colors = ['#1f77b4', '#d62728']
    
    for i, proto in enumerate(protocols):
        proto_data = grouped[grouped['protocol'] == proto].sort_values('fw_size_bytes')
        x_kb = proto_data['fw_size_bytes'] / 1024
        plt.plot(x_kb, proto_data['total_time_sec'], 
                 marker=markers[i%len(markers)], color=colors[i%len(colors)],
                 linestyle='-' if 'Custom' in proto else '--',
                 label=proto)
                 
    plt.title(f'FOTA Update Time vs. Firmware Size (PER = {target_loss}%)')
    plt.xlabel('Firmware Size (KB)')
    plt.ylabel('FOTA Update Time (s)')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(loc='best')
    
    plt.savefig(f'fig2_time_vs_size_{target_loss}pct.png', dpi=300)
    plt.close()
    print(f"Saved fig2_time_vs_size_{target_loss}pct.png")

def plot_overhead_bar(df, target_size=524288, label_size="512KB"):
    sub_df = df[df['fw_size_bytes'] == target_size]
    if sub_df.empty:
        return
        
    grouped = sub_df.groupby(['protocol', 'loss_rate_pct'])['overhead_pct'].mean().reset_index()
    
    plt.figure(figsize=(8, 6))
    protocols = grouped['protocol'].unique()
    loss_rates = sorted(grouped['loss_rate_pct'].unique())
    
    x = np.arange(len(loss_rates))
    width = 0.35
    
    for i, proto in enumerate(protocols):
        proto_data = grouped[grouped['protocol'] == proto].set_index('loss_rate_pct')
        y = proto_data.reindex(loss_rates)['overhead_pct'].fillna(0)
        
        offset = width/2 if i == 0 else -width/2
        plt.bar(x - offset, y, width, label=proto, alpha=0.8, color='#1f77b4' if 'Custom' in proto else '#d62728')
        
    plt.title(f'Retransmission Overhead vs. Packet Error Rate ({label_size})')
    plt.xlabel('Packet Error Rate (%)')
    plt.ylabel('Communication Overhead (%)')
    plt.xticks(x, [f"{l}%" for l in loss_rates])
    plt.grid(axis='y', linestyle=':', alpha=0.7)
    plt.legend(loc='upper left')
    
    plt.savefig(f'fig3_overhead_bar_{label_size}.png', dpi=300)
    plt.close()
    print(f"Saved fig3_overhead_bar_{label_size}.png")

if __name__ == "__main__":
    print("Loading FOTA CSV data...")
    df = load_data()
    if df is not None:
        print(f"Data loaded successfully. Total valid rows: {len(df)}")
        
        # 각 용량별 시간에 따른 로스율 그래프
        plot_time_vs_loss(df, target_size=524288, label_size="512KB")
        plot_time_vs_loss(df, target_size=262144, label_size="256KB")
        plot_time_vs_loss(df, target_size=131072, label_size="128KB")
        plot_time_vs_loss(df, target_size=65536,  label_size="64KB")
        
        # 용량별 시간 그래프
        plot_time_vs_size(df, target_loss=0.01)
        plot_time_vs_size(df, target_loss=0.005) # 64KB용
        
        # 오버헤드율 막대 그래프
        plot_overhead_bar(df, target_size=524288, label_size="512KB")
        plot_overhead_bar(df, target_size=65536,  label_size="64KB")
        
        print("\nAll plots generated successfully! Check the current directory for PNG files.")
