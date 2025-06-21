import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app_services import SolarPanels

sp = SolarPanels()

# set page config
st.set_page_config(
    page_title='Solar Savings',
    page_icon="☀️",
    layout='wide',
    initial_sidebar_state='auto',
)

# dashboard title
st.title('☀️ Solar Installation Savings Calculator')

# sidebar
st.sidebar.title('Info')
st.sidebar.write(f'''
MVP for solar installation savings calculator. Improvements to come:
- Add battery storage
- Add time-of-use tariffs
- Option to select from real tariffs (eg integration with Octopus API)
- Option to select from real solar panel installations
- Personalise demand profile to customer
- Investigate efficiency. Unsure if efficiency of inverter is included in
the solar data. Efficiency of PID control of diverter is not currently included

Created by Adam Vaughan, June 2025.
''')

# split main content into two columns
col1, col2 = st.columns([2,1])

# right-side column for user input
with col2:
    # form with dropdowns for user to select import/export tariff and costs
    with st.form(key='tariff_form'):
        st.subheader('Tariff')

        # tools to select tariff style from dropdown and tariff costs from sliders
        tariff_style = st.selectbox(
            'Select tariff style',
            options=['Flat'],
            index=0,
            help='Currently only flat tariffs. Time-of-use tariffs increase savings with a battery installation.'
        )
        import_cost = st.slider('Import rate (p/kWh)', 0, 80, sp.IMPORT_COST, help='Default = 27 p/kWh (Flexible Octopus as of June 2025)')
        export_cost = st.slider('Export rate (p/kWh)', 0, 80, sp.EXPORT_COST, help='Default = 15 p/kWh (Outgoing Octopus as of June 2025)')

        st.divider()
        st.subheader('Solar Installation')

        # tools to select nominal power and upfront cost of solar installation from sliders
        nominal_power = st.slider('Nominal power (kWp)', 0., 15., 3.2, step=0.1, help='Default = 3.2 kWp')
        upfront_cost = st.slider('Upfront cost (£)', 0, 15000, 5000, step=100, help='Default = £5000')

        st.divider()
        st.subheader('Battery')

        # add code here to select battery size and cost
        st.write('Coming soon...')
        
        # submit button to update graphs and metrics
        submit_button = st.form_submit_button(label='Calculate Savings', type='primary')

# left-side column for displaying results
with col1:
    # use inputted information to return savings dataframe and aggregate the data to monthly
    df = sp.calculate_costs(import_cost, export_cost, nominal_power)
    monthly_df = df.resample('MS').sum()

    # display key metrics: annual saving on left and payback period on right
    col11, col12 = st.columns([1,1])
    
    with col11:
        st.metric('Estimated annual saving', f'£{df['solar_saving'].sum():.0f}', border=True,
                  help=f'Cost with no solar =  £{df['demand_cost_no_solar'].sum():.0f}, cost with solar = £{df['demand_cost_with_solar'].sum():.0f}')
        
    with col12:
        st.metric('Estimated payback period', f'{upfront_cost / df['solar_saving'].sum():.1f} years', border=True)
                 
    # monthly savings bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_df.index, y=monthly_df['solar_saving'], name='Saving', marker_color='green'))
    fig.add_trace(go.Bar(x=monthly_df.index, y=monthly_df['demand_cost_no_solar'], name='Cost - no solar', marker_color='grey', visible='legendonly'))
    fig.add_trace(go.Bar(x=monthly_df.index, y=monthly_df['demand_cost_with_solar'], name='Cost - with solar', marker_color='gold', visible='legendonly'))
    fig.update_layout(
        title='Estimated Monthly Savings',
        xaxis_title='Month',
        yaxis_title='Saving or cost (£)'
    )
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

    # sample day bar/scatter chart. This might be useful for customers who would like
    # more explanation as to where the savings come from.
    # @TODO: allow the user to select the day they want to see
    day_df = df.loc[df.index.date == pd.Timestamp('2024-07-10').date()]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=day_df.index, y=day_df['demand_kwh'], name='Demand', marker_color='blue'))
    fig.add_trace(go.Bar(x=day_df.index, y=day_df['solar_kwh'], name='Solar', marker_color='orange'))
    fig.add_trace(go.Scatter(x=day_df.index, y=day_df['solar_saving'], name='Saving', marker_color='green'))
    fig.add_trace(go.Scatter(x=day_df.index, y=day_df['demand_cost_no_solar'], name='Cost - no solar', marker_color='grey', visible='legendonly'))
    fig.add_trace(go.Scatter(x=day_df.index, y=day_df['demand_cost_with_solar'], name='Cost - with solar', marker_color='gold', visible='legendonly'))
    fig.update_layout(
        title='Sample summer day',
        xaxis_title='Time of day',
        yaxis_title='Energy (kWh) or cost/saving (£)',
    )
    st.plotly_chart(fig, use_container_width=True)
