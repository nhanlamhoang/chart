# Import library
import pandas as pd
from sqlalchemy import create_engine
import urllib
from unidecode import unidecode
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc, dash_table, Input, Output
dash.dash_table.DataTable
import plotly.graph_objects as go
import numpy as np


server = '10.12.24.26'
database = 'BIOSecurity'
username = 'hr'
password = 'nN@12345678910'
params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password}"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")




# PA01 Headcount
file_excel = r'D:\1. TCV\1. Data Source\1.Headcount Data\PA01_Headcount Master Data.xlsx'
df_excel = pd.read_excel(file_excel, engine='openpyxl')

def clean_emp_id(x):
    try:
        return str(int(float(x))).strip()
    except:
        return ''

df_excel['Employee ID'] = df_excel['Employee ID'].apply(clean_emp_id)
df_excel = df_excel[df_excel['Employee ID'] != '']



#PA01 DIM Master

file_excel = r'D:\1. TCV\1. Data Source\1.Headcount Data\PA01_Headcount Master Data.xlsx'
df_dim_table_master = pd.read_excel(file_excel, sheet_name='Dim Table Master', engine='openpyxl')

# Bỏ dòng rỗng ở 'Project Code'
df_dim_table_master = df_dim_table_master.dropna(subset=['Project Code'])
df_dim_table_master = df_dim_table_master[df_dim_table_master['Project Code'].astype(str).str.strip() != '']

# Chuẩn hóa tên cột để xử lý chính xác (giữ bản ở bên phải)
df_dim_table_master.columns = [col.strip().lower() for col in df_dim_table_master.columns]

# Giữ lại cột trùng nhưng lấy phiên bản cuối cùng (giữ "Branch Name" bên phải)
df_dim_table_master = df_dim_table_master.loc[:, ~df_dim_table_master.columns.duplicated(keep='last')]

# (Tùy chọn) Đổi lại định dạng đẹp để hiển thị
df_dim_table_master.columns = [col.title().replace('_', ' ') for col in df_dim_table_master.columns]


# DB Attendance
query = f'''
SELECT 
    id, pers_person_pin, update_time, auth_area_name, att_date, att_datetime, att_time, auth_dept_name, device_id, device_name
FROM [BIOSecurity].[dbo].[att_transaction]
'''

# Đọc dữ liệu từ SQL Server
df1 = pd.read_sql(query, engine)

# Lọc null
df1['pers_person_pin'] = df1['pers_person_pin'].astype(str).str.strip()
df1 = df1[df1['pers_person_pin'] != '']

# Lấy bản ghi có att_date mới nhất theo pers_person_pin
latest_attendance_info = df1.sort_values('att_date', ascending=False).groupby('pers_person_pin', as_index=False).first()

# Giữ lại các cột cần thiết
latest_attendance_info = latest_attendance_info[['pers_person_pin', 'att_date', 'auth_area_name']]


#Active headcount with attendance check
df_excel['Onboarding Date_TCV'] = pd.to_datetime(df_excel['Onboarding Date_TCV'], errors='coerce')
df_excel['Termination Date'] = pd.to_datetime(df_excel['Termination Date'], errors='coerce')

# Lọc nhân sự đang active
today = pd.Timestamp(datetime.today().date())
current_headcount = df_excel[
    (df_excel['Onboarding Date_TCV'] <= today) &
    (
        df_excel['Termination Date'].isna() |
        (df_excel['Termination Date'] >= today)
    )
]

# Đổi tên key trong bảng chấm công để khớp với df_excel
latest_attendance_info_renamed = latest_attendance_info.rename(columns={
    'pers_person_pin': 'Employee ID'
})

# Merge dữ liệu chấm công vào bảng nhân sự
df_merged = pd.merge(
    current_headcount,
    latest_attendance_info_renamed[['Employee ID', 'att_date', 'auth_area_name']],
    on='Employee ID',
    how='left'  # giữ nguyên toàn bộ nhân sự
)

df_merged_filtered = df_merged[['Employee ID', 'Branch', 'Project','Job Position','Onboarding Date_TCV','Last Working Date', 'att_date', 'auth_area_name']]

df_merged_filtered_2 = pd.merge(
    df_merged_filtered,
    df_dim_table_master[['Project Name', 'Division Name', 'Unit Name']],
    left_on='Project',
    right_on='Project Name',
    how='left'
)

# Danh sách project client office
projects_to_update = ['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota', 'MB Ageas Life']

# Gán 'Client Office' cho các project được chỉ định
df_merged_filtered_2['auth_area_name'] = np.where(
    df_merged_filtered_2['Project'].isin(projects_to_update),
    'Client Office',
    df_merged_filtered_2['auth_area_name']  # giữ nguyên nếu không khớp
)

df_merged_filtered_2


import dash
from dash import dcc, html, dash_table
import pandas as pd
import plotly.express as px

# Giả định df_merged_filtered_2 đã có sẵn, bạn thay bằng dữ liệu thực tế
df_dashboard = df_merged_filtered_2.copy()

# Tính toán tổng quan
total_headcount = df_dashboard["Employee ID"].count()
total_attendance = df_dashboard["att_date"].notna().sum()
attendance_rate = round((total_attendance / total_headcount) * 100, 2)
missing_attendance = total_headcount - total_attendance

# Group theo Division
summary_by_division = df_dashboard.groupby("Division Name").agg(
    Total_Active_Headcount=("Employee ID", "count"),
    Total_Attendance_Check=("att_date", lambda x: x.notna().sum())
).reset_index()

summary_by_division["Attendance_Rate_%"] = round(
    (summary_by_division["Total_Attendance_Check"] / summary_by_division["Total_Active_Headcount"]) * 100, 2)
summary_by_division["Total_Missing_Attendance"] = (
    summary_by_division["Total_Active_Headcount"] - summary_by_division["Total_Attendance_Check"]
)
summary_by_division = summary_by_division.sort_values(by="Total_Missing_Attendance", ascending=False)

# Group theo Project
summary_by_project = df_dashboard[df_dashboard["Division Name"] == "Contact Center"] \
    .groupby("Project").agg(
    Total_Active_Headcount=("Employee ID", "count"),
    Total_Attendance_Check=("att_date", lambda x: x.notna().sum())
).reset_index()
summary_by_project["Attendance_Rate_%"] = round(
    (summary_by_project["Total_Attendance_Check"] / summary_by_project["Total_Active_Headcount"]) * 100, 2)
summary_by_project["Total_Missing_Attendance"] = (
    summary_by_project["Total_Active_Headcount"] - summary_by_project["Total_Attendance_Check"]
)
summary_by_project = summary_by_project.sort_values(by="Total_Missing_Attendance", ascending=False)

# Danh sách project được đánh nhãn là Client Office
client_projects = ['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota', 'MB Ageas Life','Honda']

# Gán nhãn Status
summary_by_project["Status"] = summary_by_project.apply(
    lambda row: "Client Office" if row["Project"] in client_projects
    else "Completed" if row["Attendance_Rate_%"] >= 100
    else "Missing",
    axis=1
)

# Sắp xếp ưu tiên 'Missing' trước, rồi theo Total_Missing_Attendance giảm dần
summary_by_project["Status_Sort"] = summary_by_project["Status"].apply(lambda x: 0 if x == "Missing" else 1)
summary_by_project = summary_by_project.sort_values(
    by=["Status_Sort", "Total_Missing_Attendance"],
    ascending=[True, False]
).drop(columns="Status_Sort")  # Xóa cột phụ


# Group theo auth_area_name
summary_by_auth_area = (
    df_dashboard.fillna({"auth_area_name": "Missing"})
    .groupby("auth_area_name")
    .agg(Employee_Count=("Employee ID", "count"))
    .reset_index()
    .sort_values(by="Employee_Count", ascending=False)
)


# ---------- Biểu đồ 100% stacked theo tỷ lệ phần trăm ----------
df_percent = summary_by_division[["Division Name", "Total_Attendance_Check", "Total_Missing_Attendance"]].copy()
df_percent["Total"] = df_percent["Total_Attendance_Check"] + df_percent["Total_Missing_Attendance"]
df_percent["Attendance_%"] = round(df_percent["Total_Attendance_Check"] / df_percent["Total"] * 100, 2)
df_percent["Missing_%"] = round(df_percent["Total_Missing_Attendance"] / df_percent["Total"] * 100, 2)

df_percent_long = df_percent.melt(
    id_vars="Division Name",
    value_vars=["Attendance_%", "Missing_%"],
    var_name="Status",
    value_name="Percent"
)
df_percent_long["Status"] = df_percent_long["Status"].replace({
    "Attendance_%": "Attendance",
    "Missing_%": "Missing"
})

fig_division_stack_pct = px.bar(
    df_percent_long,
    y="Division Name",
    x="Percent",
    color="Status",
    orientation="h",
    text="Percent",
    color_discrete_map={
        "Attendance": "#88ccee",
        "Missing": "#f4a261"
    },
    title="Attendance Distribution by Division (% of Headcount)"
)

fig_division_stack_pct.update_layout(
    barmode="stack",
    xaxis=dict(tickformat=".0f", title="Percent"),
    yaxis=dict(title="Division"),
    legend_title_text='',
    height=400,
    margin=dict(l=300, r=40, t=50, b=40)
)

fig_division_stack_pct.update_traces(textposition="inside", textfont_size=12)



# ---------- Dash App ----------
app = dash.Dash(__name__)
app.title = "Attendance Dashboard"

app.layout = html.Div([
    html.H1("Employee Attendance Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.H3("Total Active Headcount"),
             html.P(f"{total_headcount}", style={'fontSize': '28px'})
        ], className="metric"),

        html.Div([
            html.H3("Total Attendance Check"),
            html.P(f"{total_attendance}", style={'fontSize': '28px'})
        ], className="metric"),

        html.Div([
            html.H3("Attendance Rate (%)"),
            html.P(f"{attendance_rate}%", style={'fontSize': '28px'})
        ], className="metric"),

        html.Div([
            html.H3("Total Missing Attendance"),
            html.P(f"{missing_attendance}", style={'fontSize': '28px'})
        ], className="metric"),
        

        
    ], style={'display': 'flex', 'justifyContent': 'space-around'}),

    html.H2("Division-wise Attendance Metrics"),
    dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in summary_by_division.columns],
        data=summary_by_division.to_dict('records'),
        style_cell={'textAlign': 'center'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#f2f2f2'},
        style_table={'margin': '20px', 'overflowX': 'auto'}
    ),

    html.H2("Employee Count by Authorization Area"),
    dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in summary_by_auth_area.columns],
        data=summary_by_auth_area.to_dict('records'),
        style_cell={'textAlign': 'center'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#e6ffe6'},
        style_table={'margin': '20px', 'overflowX': 'auto'}
    ),

    html.H2("Division-wise Attendance Visual (% Normalized to 100%)"),
    dcc.Graph(figure=fig_division_stack_pct),

    html.H2("Project-wise Attendance Metrics"),
    dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in summary_by_project.columns],
        data=summary_by_project.to_dict('records'),
        style_cell={'textAlign': 'center'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#e8f4fc'},
        style_table={'margin': '10px', 'overflowX': 'auto'},

        # 🎨 Highlight theo Status
        style_data_conditional=[
            {
                'if': {'filter_query': '{Status} = "Client Office"'},
                'backgroundColor': '#f0f0f0',
                'color': '#333333',
                'fontWeight': 'normal'
            },
            {
                'if': {'filter_query': '{Status} = "Completed"'},
                'backgroundColor': '#e6ffed',
                'color': '#007f3f',
                'fontWeight': 'bold'
            },
            {
                'if': {'filter_query': '{Status} = "Missing"'},
                'backgroundColor': '#ffe6e6',
                'color': '#cc0000',
                'fontWeight': 'bold'
            }
        ]
    )
])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
