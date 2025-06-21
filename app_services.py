import pandas as pd
import os

class SolarPanels:
    def __init__(self):
        # define default values for dropdown options
        self.IMPORT_TARIFF_NAME = 'Flexible Octopus'
        self.EXPORT_TARIFF_NAME = 'Outgoing Octopus'
        self.IMPORT_COST = 27 #p/kWh, Flexible Octopus as of June 2025
        self.EXPORT_COST = 15 #p/kWh, Outgoing Octopus as of June 2025

        self.df = self.get_demand_and_solar_data()

    def create_filepath(self, filename:str):
        ''' Create a filepath that works on all operating systems '''
        return os.path.join(os.getcwd(), 'raw_data', filename)
    
    def get_full_index_df(self) -> pd.DataFrame:
        ''' we have about a year and a half of demand data. For the first pass, let's just use
            the full year of 2024. This returns a dataframe that covers this desired range '''

        full_index = pd.date_range(start='2024-01-01 00:00:00', end='2024-12-31 23:30:00', freq='30min', tz='UTC')
        full_index_df = pd.DataFrame(index=full_index)

        return full_index_df
    
    def get_demand_data(self) -> pd.DataFrame:
        # read in the demand data, rename columns, set start of HH as index and sort
        demand_filepath = self.create_filepath('consumption.csv')
        demand_df = pd.read_csv(demand_filepath, sep=', ', engine='python')
        demand_df = demand_df.rename(columns={'Start': 'start', 'End': 'end', 'Consumption (kWh)': 'demand_kwh'})
        demand_df['start'] = pd.to_datetime(demand_df['start'], utc=True)
        demand_df['end'] = pd.to_datetime(demand_df['end'], utc=True)
        demand_df.index = demand_df['start']
        demand_df = demand_df.sort_index()

        # map onto desired range
        full_index_df = self.get_full_index_df()
        demand_df = pd.merge(full_index_df, demand_df, how='left', left_index=True, right_index=True)
        demand_df.index.name = 'timestamp'

        # the only missing data is 1-6 July. Fill in with the previous week's data
        demand_df['demand_kwh'] = demand_df['demand_kwh'].fillna(demand_df['demand_kwh'].shift(48*7))

        print(f'Demand data has {demand_df['demand_kwh'].isna().sum()} missing values')

        # @TODO: it would be worth putting in some sense checks here to look for strange values.
        # For now I've just eyeballed the graphs

        return demand_df
    
    def get_solar_data(self) -> pd.DataFrame:
        # read in the solar data
        solar_filepath = self.create_filepath('Timeseries_51.339_-1.262_SA3_3kWp_crystSi_14_30deg_15deg_2005_2005.csv')
        solar_df = pd.read_csv(solar_filepath, skiprows=10, skipfooter=11, engine='python')
        solar_df['time'] = pd.to_datetime(solar_df['time'], format='%Y%m%d:%H%M', utc=True)

        # shift the year to 2024 to merge with the demand data, subtract 10 minutes
        # to align with the start of the hour
        # @TODO: why does the data start at 10 minutes past the hour?
        solar_df['time'] = solar_df['time'].apply(lambda x: x.replace(year=2024))
        solar_df['time'] = solar_df['time'] - pd.Timedelta(minutes=10)
        solar_df.index = solar_df['time']
        solar_df = solar_df.sort_index()

        # map onto the desired range
        full_index_df = self.get_full_index_df()
        solar_df = pd.merge(full_index_df, solar_df, how='left', left_index=True, right_index=True)
        solar_df = solar_df.ffill(limit=1)

        # calculate the energy produced in kWh per half hour
        solar_df['solar_kwh'] = solar_df['P'] * 0.5 / 1000

        # we have one day of missing data: Feb 29th as we've gone from non leap year to leap year :/
        # fill this with the previous day's data
        solar_df['solar_kwh'] = solar_df['solar_kwh'].fillna(solar_df['solar_kwh'].shift(48))

        print(f'Solar data has {solar_df['solar_kwh'].isna().sum()} missing values')

        # @TODO: data checks here too

        return solar_df
    
    def get_demand_and_solar_data(self) -> pd.DataFrame:
        ''' Merge the demand and solar data into a single dataframe '''

        demand_df = self.get_demand_data()
        solar_df = self.get_solar_data()

        return pd.merge(demand_df[['demand_kwh']], solar_df[['solar_kwh']], how='left', left_index=True, right_index=True)
    
    def calculate_costs(self, import_cost:float, export_cost:float, nominal_power:float) -> pd.DataFrame:
        ''' Calculate costs with and without solar panels and hence the savings '''

        df = self.df.copy()

        # scale the solar power by the nominal power of the installation
        df['solar_kwh'] = df['solar_kwh'] * nominal_power / 3.2

        # calculate the excess of solar compared to demand. This is zero
        # if solar is less than demand, otherwise it's the difference. Vice-versa
        # for shortfall solar
        df['excess_solar_kwh'] = (df['solar_kwh'] - df['demand_kwh']).clip(lower=0)
        df['shortfall_solar_kwh'] = (df['demand_kwh'] - df['solar_kwh']).clip(lower=0)

        # calculate the cost of demand with no solar
        df['demand_cost_no_solar'] = df['demand_kwh'] * import_cost/100 # £

        # now calculate the cost of demand with solar
        df['demand_cost_with_solar'] = (df['shortfall_solar_kwh'] * import_cost/100) - (df['excess_solar_kwh'] * export_cost/100) # £

        # and the solar saving
        df['solar_saving'] = df['demand_cost_no_solar'] - df['demand_cost_with_solar']

        # @TODO: 100% efficiency assumed. This will not be the case in practice:
        # - diverter has PID controller which takes time to switch between import and export
        # - inverter efficiency

        return df