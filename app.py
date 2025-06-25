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


# In[3]:


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


# In[4]:


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


# In[5]:


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


# In[9]:


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

# Danh sách project cần thay đổi
projects_to_update = ['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota', 'MB Ageas Life']

# Gán 'Client Office' cho các project được chỉ định
df_merged_filtered_2['auth_area_name'] = np.where(
    df_merged_filtered_2['Project'].isin(projects_to_update),
    'Client Office',
    df_merged_filtered_2['auth_area_name']  # giữ nguyên nếu không khớp
)

df_merged_filtered_2


# In[ ]:


df = df_merged_filtered.copy()

# MEASURE

#Tính metric Attendance theo Project
attendance_by_project_base = df.groupby('Project').agg({
    'Employee ID': 'count',
    'auth_area_name': lambda x: x.notna().sum()
}).reset_index()
attendance_by_project_base.columns = ['Project', 'Active Headcount', 'Attendance Account']

#Tỷ lệ Attendance (%).
attendance_by_project_base['Attendance Rate (%)'] = round(
    (attendance_by_project_base['Attendance Account'] / attendance_by_project_base['Active Headcount']) * 100, 2)

#Số lượng nhân viên thiếu check-in (Missing)
attendance_by_project_base['Missing'] = attendance_by_project_base['Active Headcount'] - attendance_by_project_base['Attendance Account']

#Gộp thông tin Division Name
attendance_by_project_base = attendance_by_project_base.merge(
    merged_info[['Project', 'Division Name']].drop_duplicates(),
    on='Project',
    how='left'
)

#Phân loại trạng thái Status
attendance_by_project_base['Status'] = attendance_by_project_base['Attendance Rate (%)'].apply(
    lambda x: '✅ Done' if x >= 100 else '❌ Missing'
)

#Tổng hợp Attendance theo Division
attendance_by_division = attendance_by_project_base.groupby('Division Name').agg({
    'Active Headcount': 'sum',
    'Attendance Account': 'sum',
    'Missing': 'sum'
}).reset_index()
attendance_by_division['Attendance Rate (%)'] = round(
    (attendance_by_division['Attendance Account'] / attendance_by_division['Active Headcount']) * 100, 2
)
attendance_by_division['Status'] = attendance_by_division['Attendance Rate (%)'].apply(
    lambda x: '✅ Done' if x >= 100 else '❌ Missing'
)

#Tính trạng thái đã/không Attendance theo Division
employee_check = merged_info.copy()
employee_check['Checked'] = employee_check['auth_area_name'].notna()
attendance_status_div = employee_check.groupby(['Division Name', 'Checked'])['Employee ID'].nunique().reset_index(name='Count')
attendance_status_div['Checked'] = attendance_status_div['Checked'].map({True: 'Có', False: 'Không'})

#Tính phân bổ theo auth_area_name
auth_area_distribution = df.copy()
auth_area_distribution = auth_area_distribution[~auth_area_distribution['auth_area_name'].isna()]
auth_area_summary = auth_area_distribution.groupby('auth_area_name')['Employee ID'].nunique().reset_index()
auth_area_summary = auth_area_summary.sort_values(by='Employee ID', ascending=True)


# Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Attendance Overview Dashboard"),

    html.Div([
        html.Label("Division Name"),
        dcc.Dropdown(
            id='division-filter',
            options=[{'label': div, 'value': div} for div in sorted(attendance_by_project_base['Division Name'].dropna().unique())],
            placeholder="Select",
            multi=False
        )
    ], style={'width': '40%', 'marginBottom': '30px'}),

    html.Div([
    html.Label("Bộ lọc nhóm Client Office"),
    dcc.RadioItems(
        id='client-filter',
        options=[
            {'label': 'Tất cả', 'value': 'all'},
            {'label': 'Chỉ Client Office', 'value': 'client_only'},
            {'label': 'Không bao gồm Client Office', 'value': 'exclude_client'}
        ],
        value='all',
        labelStyle={'display': 'inline-block', 'margin-right': '15px'}
    )
], style={'marginBottom': '30px'}),

    html.Div(id='metric-output'),

    dcc.Graph(id='pie-overall'),
    dcc.Graph(id='bar-checkin-status'),
    dcc.Graph(id='bar-auth-area'),


    html.H3("Tỷ lệ Attendance theo Project (Biểu đồ 100%)"),
    dcc.Graph(id='bar-incomplete'),

    html.H3("Chi tiết theo Project"),
    dash_table.DataTable(
        id='project-table',
        columns=[
            {'name': 'Project', 'id': 'Project'},
            {'name': 'Division Name', 'id': 'Division Name'},
            {'name': 'Active Headcount', 'id': 'Active Headcount'},
            {'name': 'Attendance Account', 'id': 'Attendance Account'},
            {'name': 'Missing', 'id': 'Missing'},
            {'name': 'Attendance Rate (%)', 'id': 'Attendance Rate (%)'},
            {'name': 'Status', 'id': 'Status'}
        ],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'},
        export_format='csv',
        export_headers='display'
    ),

    html.H3("Chi tiết theo Division Name"),
    dash_table.DataTable(
        id='division-table',
        columns=[
            {'name': 'Division Name', 'id': 'Division Name'},
            {'name': 'Active Headcount', 'id': 'Active Headcount'},
            {'name': 'Attendance Account', 'id': 'Attendance Account'},
            {'name': 'Missing', 'id': 'Missing'},
            {'name': 'Attendance Rate (%)', 'id': 'Attendance Rate (%)'},
            {'name': 'Status', 'id': 'Status'}
        ],
        data=attendance_by_division.sort_values(by='Attendance Rate (%)', ascending=False).to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'},
        export_format='csv',
        export_headers='display'
    )
])


@app.callback(
    [
        Output('metric-output', 'children'),
        Output('pie-overall', 'figure'),
        Output('bar-incomplete', 'figure'),
        Output('project-table', 'data'),
        Output('bar-checkin-status', 'figure'),
        Output('bar-auth-area', 'figure') 
    ],
    [
        Input('division-filter', 'value'),
        Input('client-filter', 'value')  # ← dòng thêm
    ]
)

def update_dashboard(selected_division, client_filter): 
    if selected_division:
        df_filtered = attendance_by_project_base[attendance_by_project_base['Division Name'] == selected_division]
        attendance_status_filtered = attendance_status_div[attendance_status_div['Division Name'] == selected_division]
    else:
        df_filtered = attendance_by_project_base.copy()
        attendance_status_filtered = attendance_status_div.copy()

    # Lọc theo nhóm Client Office
    if client_filter == 'client_only':
        df_filtered = df_filtered[df_filtered['Project'].isin(
            ['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota']
        )]
    elif client_filter == 'exclude_client':
        df_filtered = df_filtered[~df_filtered['Project'].isin(
            ['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota']
        )]

    total_active = df_filtered['Active Headcount'].sum()
    total_attend = df_filtered['Attendance Account'].sum()
    rate = round((total_attend / total_active) * 100, 2) if total_active else 0

    client_office_count = df[df['auth_area_name'] == 'Client Office']['Employee ID'].nunique()

    metrics = html.Div([
        html.Div([
            html.H3("Total Active Headcount"),
            html.H2(f"{total_active}")
        ], style={'width': '25%', 'display': 'inline-block'}),
        html.Div([
            html.H3("Total Attendance Account"),
            html.H2(f"{total_attend}")
        ], style={'width': '25%', 'display': 'inline-block'}),
        html.Div([
            html.H3("Attendance Rate"),
            html.H2(f"{rate}%")
        ], style={'width': '25%', 'display': 'inline-block'}),
        html.Div([
            html.H3("Client Office Count"),
            html.H2(f"{client_office_count}")
        ], style={'width': '25%', 'display': 'inline-block'}),
    ], style={'textAlign': 'center', 'marginBottom': '40px'})

    pie_fig = px.pie(
        names=['Attendance', 'Absence'],
        values=[total_attend, total_active - total_attend],
        title='Overall Attendance Rate',
        color_discrete_sequence=['#00b894', '#636e72']
    )

    # 100% Stacked Bar Chart
    # Biểu đồ stacked 100% cải tiến
    stack_df = df_filtered.copy()
    stack_df['Absent'] = stack_df['Active Headcount'] - stack_df['Attendance Account']
    stack_df['Yes Percent'] = round((stack_df['Attendance Account'] / stack_df['Active Headcount']) * 100, 1)
    stack_df['No Percent'] = round((stack_df['Absent'] / stack_df['Active Headcount']) * 100, 1)

    # Sắp xếp giảm dần theo % attendance
    stack_df = stack_df.sort_values(by='Yes Percent', ascending=False)

    fig_bar = go.Figure()

    fig_bar.add_trace(go.Bar(
        y=stack_df['Project'],
        x=stack_df['Yes Percent'],
        name='Có Attendance',
        orientation='h',
        marker_color='#08306b',  # Xanh dương đậm
        text=stack_df['Yes Percent'].astype(str) + '%',
        textposition='inside'
    ))

    fig_bar.add_trace(go.Bar(
        y=stack_df['Project'],
        x=stack_df['No Percent'],
        name='Không Attendance',
        orientation='h',
        marker_color='#fb6a4a',  # Cam đỏ nhạt
        text=stack_df['No Percent'].astype(str) + '%',
        textposition='inside'
    ))

    fig_bar.update_layout(
        barmode='stack',
        title='Tỷ lệ Attendance theo Project (Stacked 100%)',
        xaxis=dict(title='Tỷ lệ %', range=[0, 100], ticksuffix='%'),
        yaxis=dict(title='Project', automargin=True),
        legend=dict(orientation='h', y=-0.25),
        margin=dict(l=180, r=20, t=50, b=50),
        height=min(700, 25 * len(stack_df) + 150),  # Giới hạn chiều cao không quá 700
        font=dict(size=12)
    )


    table_data = df_filtered.sort_values(by='Missing', ascending=False).to_dict('records')


    attendance_status_filtered = attendance_status_filtered.sort_values(by='Count', ascending=False)
    bar_checkin = px.bar(
        attendance_status_filtered,
        x='Division Name',
        y='Count',
        color='Checked',
        barmode='group',
        text='Count',
        title='Dự án có/không Attendance theo Division',
        color_discrete_map={'Có': '#00b894', 'Không': '#d63031'}
    )
    bar_checkin.update_traces(textposition='outside')

    auth_area_distribution = df.copy()
    auth_area_distribution = auth_area_distribution.merge(
    merged_info[['Project', 'Division Name']].drop_duplicates(),
    on='Project',
    how='left'
    )
    if selected_division:
        auth_area_distribution = auth_area_distribution[
            auth_area_distribution['Division Name'] == selected_division
        ]

    if client_filter == 'client_only':
        auth_area_distribution = auth_area_distribution[
            auth_area_distribution['Project'].isin(['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota'])
        ]
    elif client_filter == 'exclude_client':
        auth_area_distribution = auth_area_distribution[
            ~auth_area_distribution['Project'].isin(['Heineken', 'MB Bank', 'Daikin HCM', 'HVBB (Heineken)_HCM', 'Toyota'])
        ]

    auth_area_distribution = auth_area_distribution[~auth_area_distribution['auth_area_name'].isna()]
    auth_area_summary = auth_area_distribution.groupby('auth_area_name')['Employee ID'].nunique().reset_index()
    auth_area_summary = auth_area_summary.sort_values(by='Employee ID', ascending=True)

    bar_auth_area = px.bar(
        auth_area_summary,
        x='Employee ID',
        y='auth_area_name',
        orientation='h',
        text='Employee ID',
        labels={'Employee ID': 'Số lượng', 'auth_area_name': 'Khu vực'},
        title='Phân bổ nhân sự theo Khu vực Attendance',
        color_discrete_sequence=['#2980b9']
    )
    bar_auth_area.update_traces(textposition='outside')


    return metrics, pie_fig, fig_bar, table_data, bar_checkin, bar_auth_area

local: app.run(debug=True)
