import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import os
import base64


# Set the path for the logo
logo_path = "logo.png"  # Assuming the logo file is in the same directory as your script

# Configure the Streamlit page
st.set_page_config(
    page_title="ProCare Dashboard",
    page_icon=logo_path,
    layout="wide"
)

# Function to display the logo in the center
def display_logo():
    # Ensure the logo is loaded from the correct location
    if os.path.exists(logo_path):
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="data:image/png;base64,{get_image_base64(logo_path)}" style="width: 160px;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("Logo not found. Please check the file path.")

# Function to get the base64 encoding of the logo
def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# Function to display the header with the centered logo
def display_header():
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #2E8B57; margin-top: 10px;">ProCare Medical Insurance Company Dashboard</h1>
            <h3 style="color: #444;">EECE 433 Fall 2024-2025</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Function to display team names in the sidebar
def display_team_names():
    st.sidebar.markdown(
        """
        <div style="margin-top: 20px;">
            <p><b>"ProCare: Keeping you healthy, so you can laugh at life's little accidents!"</b></p>
            <ul style="list-style-type: none; padding: 0;">
                <li><b> Presented By: </b></li>
                <li><b>- Kamel Soubra</b></li>
                <li><b>- Lama Hasbini</b></li>
                <li><b>- Omar Succcar</b></li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
# Database connection configuration
DB_CONFIG = {
    "dbname": "project2",
    "user": "postgres",
    "password": "kamel",
    "host": "localhost",
    "port": "5432"
}

# Connect to the database
def connect_db():
    engine = create_engine(
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    )
    return engine

# Define SQL queries as functions
def top_5_monthly_services(engine):
    query = """
        SELECT * FROM top5monthlyservicesummary
    """
    return pd.read_sql(query, engine)

def client_spending_by_hcp(engine):
    query = """
        SELECT 
            H.HealthcareProviderID, 
            H.ProviderName AS HealthcareProviderName, 
            C.ClientID, 
            CONCAT(C.FirstName, ' ', COALESCE(C.MiddleName, ''), ' ', C.LastName) AS ClientFullName, 
            SUM(P.ServiceCost) AS TotalSpending
        FROM Provide P 
        JOIN Client C ON P.ClientID = C.ClientID 
        JOIN EmployDoctor ED ON P.DoctorID = ED.DoctorID 
        JOIN HealthcareProvider H ON ED.HealthcareProviderID = H.HealthcareProviderID 
        GROUP BY H.HealthcareProviderID, H.ProviderName, C.ClientID, C.FirstName, C.MiddleName, C.LastName 
        ORDER BY TotalSpending DESC;
    """
    return pd.read_sql(query, engine)

def fraud_claims(engine):
    query = """
        SELECT 
            rc.ClientID,
            CONCAT(c.FirstName, ' ', COALESCE(c.MiddleName, ''), ' ', c.LastName) AS ClientName,
            COUNT(*) AS TotalClaims,
            SUM(rc.Amount) AS TotalAmount,
            ROUND(SUM(CASE WHEN rc.ApprovalStatus = 'Rejected' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS RejectionRate
        FROM RequestClaim rc
        JOIN Client c ON rc.ClientID = c.ClientID
        WHERE rc.DateCreated >= NOW() - INTERVAL '3 MONTH'
        GROUP BY rc.ClientID, c.FirstName, c.MiddleName, c.LastName
        HAVING COUNT(*) > 10 AND SUM(rc.Amount) > 100000 
        ORDER BY TotalClaims DESC;
    """
    data = pd.read_sql(query, engine)

    # Debugging output: Check if the dataset is empty
    if data.empty:
        print("Debug: Fraud Claims query returned no data.")
    else:
        print(f"Debug: Retrieved {len(data)} rows from Fraud Claims query.")

    return data

def high_risk_clients(engine):
    query = """
        WITH AggregatedMedicalRecords AS (
            SELECT ClientID, 
                COUNT(DISTINCT ICDCode) AS MedicalRecordCount
            FROM MedicalRecords
            GROUP BY ClientID
        ),
        AggregatedRequestClaims AS (
            SELECT ClientID, 
                SUM(CASE 
                    WHEN ApprovalStatus IN ('Approved', 'Pending') THEN Amount 
                    ELSE 0 
                END) AS TotalClaimAmount
            FROM RequestClaim
            GROUP BY ClientID
        ),
        AggregatedDependents AS (
            SELECT ClientID, COUNT(*) AS NumberOfDependents
            FROM ClientDependent
            GROUP BY ClientID
        )
        SELECT c.ClientID AS clientid,
            CONCAT(c.FirstName, ' ', COALESCE(c.MiddleName, ''), ' ', c.LastName) AS clientname,
            COALESCE(mr.MedicalRecordCount, 0) AS medicalrecordcount,
            COALESCE(rc.TotalClaimAmount, 0) AS totalclaimamount,
            COALESCE(dep.NumberOfDependents, 0) AS numberofdependents
        FROM Client c
        LEFT JOIN AggregatedMedicalRecords mr ON c.ClientID = mr.ClientID
        LEFT JOIN AggregatedRequestClaims rc ON c.ClientID = rc.ClientID
        LEFT JOIN AggregatedDependents dep ON c.ClientID = dep.ClientID
        WHERE COALESCE(mr.MedicalRecordCount, 0) > 10 
            AND COALESCE(rc.TotalClaimAmount, 0) > 100000
            AND COALESCE(dep.NumberOfDependents, 0) > 0
        ORDER BY rc.TotalClaimAmount DESC;
    """
    return pd.read_sql(query, engine)

def insurance_plan_distribution(engine):
    query = """
        SELECT 
            H.HealthcareProviderID,
            H.ProviderName AS HealthcareProviderName,
            IP.CoverageLevel AS InsurancePlanLevel,
            COUNT(DISTINCT C.ClientID) AS ClientCount
        FROM Provide P
        JOIN Client C ON P.ClientID = C.ClientID
        JOIN Sell S ON C.ClientID = S.ClientID
        JOIN Policy L ON S.PolicyNumber = L.PolicyNumber
        JOIN InsurancePlan IP ON L.InsurancePlanName = IP.InsurancePlanName
        JOIN EmployDoctor ED ON P.DoctorID = ED.DoctorID
        JOIN HealthcareProvider H ON ED.HealthcareProviderID = H.HealthcareProviderID
        GROUP BY H.HealthcareProviderID, H.ProviderName, IP.CoverageLevel
        ORDER BY H.HealthcareProviderID, IP.CoverageLevel;
    """
    data = pd.read_sql(query, engine)
    if data.empty:
        print("Debug: Insurance Plan Distribution query returned no data.")
    else:
        print(f"Debug: Retrieved {len(data)} rows from Insurance Plan Distribution query.")
    return data

def revenue_contribution_by_agent(engine):
    query = """
        SELECT 
            s.AgentID,
            a.AgentName,
            EXTRACT(YEAR FROM p.StartDate) AS Year,
            COUNT(s.ClientID) AS TotalClients,
            SUM(p.ExactCost) AS TotalRevenue,
            ROUND(SUM(a.CommissionRate / 100 * p.ExactCost), 2) AS TotalCommission,
            ROUND(SUM(p.ExactCost) - SUM(a.CommissionRate / 100 * p.ExactCost), 2) AS NetProfit
        FROM Sell s
        JOIN Policy p ON s.PolicyNumber = p.PolicyNumber
        JOIN Agent a ON s.AgentID = a.AgentID
        GROUP BY s.AgentID, a.AgentName, EXTRACT(YEAR FROM p.StartDate)
        ORDER BY TotalRevenue DESC;
    """
    return pd.read_sql(query, engine)

def medical_conditions_insights(engine):
    query = """
        WITH ConditionFrequency AS (
            SELECT mr.ConditionName, COUNT(mr.ClientID) AS ConditionCount
            FROM MedicalRecords mr
            GROUP BY mr.ConditionName
            ORDER BY ConditionCount DESC
            LIMIT 10
        ),
        ServicesForConditions AS (
            SELECT 
                cf.ConditionName,
                cf.ConditionCount,
                ms.ServiceName,
                ip.CoverageLevel,
                COUNT(DISTINCT pr.ClientID) AS ClientsServed
            FROM ConditionFrequency cf
            JOIN MedicalRecords mr ON cf.ConditionName = mr.ConditionName
            JOIN Provide pr ON mr.ClientID = pr.ClientID
            JOIN MedicalService ms ON pr.ServiceID = ms.ServiceID
            JOIN Sell sl ON mr.ClientID = sl.ClientID
            JOIN Policy pl ON sl.PolicyNumber = pl.PolicyNumber
            JOIN InsurancePlan ip ON pl.InsurancePlanName = ip.InsurancePlanName
            GROUP BY 
                cf.ConditionName, 
                cf.ConditionCount, 
                ms.ServiceName, 
                ip.CoverageLevel
        )
        SELECT 
            ConditionName,
            ConditionCount,
            ServiceName,
            CoverageLevel,
            ClientsServed
        FROM ServicesForConditions
        ORDER BY ConditionCount DESC, ConditionName, CoverageLevel, ClientsServed DESC;
    """
    return pd.read_sql(query, engine)

def company_profits(engine):
    query = """
    WITH RevenueFromPolicies AS (
        SELECT SUM(p.ExactCost - (a.CommissionRate / 100) * p.ExactCost) AS PoliciesRevenue
        FROM Policy p
        JOIN Sell s ON p.PolicyNumber = s.PolicyNumber
        JOIN Agent a ON s.AgentID = a.AgentID
        WHERE p.StartDate >= CURRENT_DATE - INTERVAL '1 year'
    ),
    RevenueFromPayments AS (
        SELECT SUM(py.Amount) AS PaymentRevenue
        FROM Pays py
        WHERE py.Date >= CURRENT_DATE - INTERVAL '1 year'
    ),
    NetRevenue AS (
        SELECT ROUND(
            (SELECT PoliciesRevenue FROM RevenueFromPolicies) + 
            (SELECT PaymentRevenue FROM RevenueFromPayments), 
            2
        ) AS TotalRevenue
    ),
    TotalEmployeeSalary AS (
        SELECT SUM(e.Salary * 12) AS TotalEmployeeSalaries
        FROM Employee e
    ),
    TotalClaimAmount AS (
        SELECT SUM(CASE WHEN rc.ApprovalStatus = 'Approved' THEN rc.Amount ELSE 0 END) AS TotalClaims
        FROM RequestClaim rc
        WHERE rc.DateCreated >= CURRENT_DATE - INTERVAL '1 year'
    ),
    NetExpenses AS (
        SELECT ROUND(
            (SELECT TotalEmployeeSalaries FROM TotalEmployeeSalary) + 
            (SELECT TotalClaims FROM TotalClaimAmount), 
            2
        ) AS TotalExpenses
    ),
    Profit AS (
        SELECT ROUND(
            (SELECT TotalRevenue FROM NetRevenue) - 
            (SELECT TotalExpenses FROM NetExpenses), 
            2
        ) AS NetProfit
    )
    SELECT 
        (SELECT TotalRevenue FROM NetRevenue) AS TotalRevenue,
        (SELECT TotalExpenses FROM NetExpenses) AS TotalExpenses,
        (SELECT NetProfit FROM Profit) AS NetProfit;
    """
    return pd.read_sql(query, engine)

def unused_providers_analysis(engine):
    query = """
        WITH ActivePolicies AS (
            SELECT s.ClientID, s.PolicyNumber, p.StartDate, p.EndDate, c.InsurancePlanName, c.HealthcareProviderID
            FROM Sell s
            INNER JOIN Policy p ON s.PolicyNumber = p.PolicyNumber
            INNER JOIN Covers c ON p.InsurancePlanName = c.InsurancePlanName
            WHERE p.EndDate >= CURRENT_DATE
        ),
        ProviderUsage AS (
            SELECT ap.ClientID, ap.HealthcareProviderID, h.ProviderName, COUNT(DISTINCT pr.ServiceID) AS ServicesUsed
            FROM ActivePolicies ap
            LEFT JOIN Provide pr ON ap.ClientID = pr.ClientID
            AND pr.DoctorID IN (
                SELECT DoctorID FROM EmployDoctor WHERE HealthcareProviderID = ap.HealthcareProviderID
            )
            LEFT JOIN HealthcareProvider h ON ap.HealthcareProviderID = h.HealthcareProviderID
            GROUP BY ap.ClientID, ap.HealthcareProviderID, h.ProviderName
        ),
        UnusedProviders AS (
            SELECT DISTINCT h.HealthcareProviderID, h.ProviderName, c.InsurancePlanName
            FROM Covers c
            LEFT JOIN ProviderUsage pu ON c.HealthcareProviderID = pu.HealthcareProviderID
            LEFT JOIN HealthcareProvider h ON c.HealthcareProviderID = h.HealthcareProviderID
            WHERE pu.ServicesUsed IS NULL
        )
        SELECT up.ProviderName AS UnusedProvider,
               up.InsurancePlanName AS CoveredPlan,
               COUNT(DISTINCT ap.ClientID) AS ClientsCovered,
               COUNT(DISTINCT ap.ClientID) AS ClientsUtilizing
        FROM UnusedProviders up
        LEFT JOIN ActivePolicies ap ON up.HealthcareProviderID = ap.HealthcareProviderID
        LEFT JOIN Provide pr ON ap.ClientID = pr.ClientID
        GROUP BY up.ProviderName, up.InsurancePlanName
        ORDER BY ClientsCovered DESC;
    """
    return pd.read_sql(query, engine)

def employee_claim_handling(engine):
    query = """
        WITH EmployeeClaimStats AS (
            SELECT 
                e.EmployeeID,
                e.FirstName || ' ' || COALESCE(e.MiddleName, '') || ' ' || e.LastName AS EmployeeName,
                rc.ApprovalStatus,
                COUNT(rc.ClientID) AS ClaimCount,
                SUM(rc.Amount) AS TotalClaimAmount
            FROM RequestClaim rc
            INNER JOIN Employee e ON rc.EmployeeID = e.EmployeeID
            GROUP BY e.EmployeeID, e.FirstName, e.MiddleName, e.LastName, rc.ApprovalStatus
        )
        SELECT 
            ecs.EmployeeID,
            ecs.EmployeeName,
            ecs.ApprovalStatus,
            ecs.ClaimCount,
            ecs.TotalClaimAmount,
            ROUND(
                (ecs.ClaimCount::DECIMAL / SUM(ecs.ClaimCount) OVER (PARTITION BY ecs.EmployeeID)) * 100, 
                2
            ) AS PercentageOfTotalClaims
        FROM EmployeeClaimStats ecs
        ORDER BY ecs.EmployeeID, ecs.ApprovalStatus;
    """
    return pd.read_sql(query, engine)

# Streamlit Interface
def main():
    engine = connect_db()
    
    display_header()
    display_logo()
    # Sidebar for query selection
    st.sidebar.title("Select Query")
    query_options = [
        "Top 5 Monthly Services",
        "Client Spending by Healthcare Provider",
        "High-Risk Clients",
        "Insurance Plan Distribution Across Healthcare Providers", 
        "Revenue Contribution by Agent",
        "Medical Conditions Insights",
        "Company Profits",
        "Unused Healthcare Providers Analysis",
        "Employee Claim Handling",
        "Fraud Claims"
    ]
    selected_query = st.sidebar.selectbox("Choose a query to view", query_options)
    
    display_team_names()
    
    if selected_query == "Top 5 Monthly Services":
        st.subheader("Top 5 Monthly Revenue-Generating Services")
        data = top_5_monthly_services(engine)
        st.dataframe(data)

        # Convert columns to a consistent format
        data.columns = [col.title() for col in data.columns]

        if not data.empty:
    # Rescale by updating the layout of the figure
            fig = px.bar(
                data,
                x="Serviceperiod",
                y="Totalgenerated",
                color="Healthcareproviderid",
                barmode="group",  # Grouped bar chart
                title="Top 5 Monthly Services by Revenue",
                labels={
                    "Serviceperiod": "Month",
                    "Totalgenerated": "Revenue",
                    "Healthcareproviderid": "Provider"
                }
            )
        
            # Update layout for better scaling
            fig.update_layout(
                height=600,  # Adjust height
                width=1000,  # Adjust width
                xaxis_title="Service Period (Month)",
                yaxis_title="Total Revenue",
                legend_title="Healthcare Providers",
                title_font_size=18,
            )

            # Display the rescaled chart in Streamlit
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available for this query.")

    elif selected_query == "Client Spending by Healthcare Provider":
        st.subheader("Client Spending by Healthcare Providers")
        data = client_spending_by_hcp(engine)
        st.dataframe(data)
    
        if not data.empty:
            # Add an option to view either all clients or a specific client
            view_option = st.radio(
                "View Option",
                ("All Clients", "Specific Client"),
                horizontal=True
            )
    
            if view_option == "All Clients":
                # Display the original bar chart for all clients
                fig = px.bar(
                    data,
                    x="healthcareprovidername",
                    y="totalspending",
                    color="clientfullname",
                    barmode="group",  # Grouped bar chart
                    title="Client Spending by Healthcare Providers (All Clients)",
                    labels={
                        "healthcareprovidername": "Provider Name",
                        "totalspending": "Spending",
                        "clientfullname": "Client"
                    }
                )
                fig.update_layout(
                    height=600,
                    width=1000,
                    xaxis_title="Healthcare Providers",
                    yaxis_title="Total Spending",
                    legend_title="Clients",
                    title_font_size=18
                )
                st.plotly_chart(fig, use_container_width=True)
    
            elif view_option == "Specific Client":
                # Dropdown to select a specific client
                client_names = data['clientfullname'].unique()  # Get unique client names
                selected_client = st.selectbox("Select a Client", client_names)
    
                # Filter data for the selected client
                client_data = data[data['clientfullname'] == selected_client]
    
                # Display a bar chart for the selected client
                st.write(f"Spending Details for {selected_client}")
                fig = px.bar(
                    client_data,
                    x="healthcareprovidername",
                    y="totalspending",
                    title=f"Spending by {selected_client}",
                    labels={
                        "healthcareprovidername": "Healthcare Provider",
                        "totalspending": "Total Spending"
                    }
                )
                fig.update_layout(
                    height=500,
                    width=800,
                    xaxis_title="Healthcare Providers",
                    yaxis_title="Total Spending",
                    title_font_size=18
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available for the selected query.")



    elif selected_query == "High-Risk Clients":
        st.subheader("High-Risk Clients")
        data = high_risk_clients(engine)
        st.dataframe(data)

        if not data.empty:
            fig = px.bar(
                data,
                x="clientname",
                y="totalclaimamount",
                color="medicalrecordcount",
                title="High-Risk Clients Based on Claims and Medical Records",
                labels={
                    "clientname": "Client",
                    "totalclaimamount": "Claim Amount",
                    "medicalrecordcount": "Medical Records"
                }
            )
            st.plotly_chart(fig)

    elif selected_query == "Fraud Claims":
        st.subheader("Fraud Claims")
        data = fraud_claims(engine)
        st.dataframe(data)
    
        if not data.empty:
            # Visualize the fraud claims
            fig = px.bar(
                data,
                x="ClientName",
                y="TotalAmount",
                color="RejectionRate",
                title="Fraud Claims Analysis",
                labels={
                    "ClientName": "Client",
                    "TotalAmount": "Total Claimed Amount",
                    "RejectionRate": "Rejection Rate (%)"
                }
            )
            st.plotly_chart(fig)
        else:
            st.warning("No fraud claims data found until now.")
    
    elif selected_query == "Insurance Plan Distribution Across Healthcare Providers":
        st.subheader("Insurance Plan Distribution Across Healthcare Providers")
        data = insurance_plan_distribution(engine)
    
        if not data.empty:
            # Extract unique healthcare providers
            healthcare_providers = data["healthcareprovidername"].unique()
            selected_provider = st.selectbox(
                "Select a Healthcare Provider to view details:", 
                options=["All"] + list(healthcare_providers)
            )
    
            # Filter data based on the selected provider
            if selected_provider != "All":
                filtered_data = data[data["healthcareprovidername"] == selected_provider]
            else:
                filtered_data = data
    
            # Display filtered data
            st.dataframe(filtered_data)
    
            # Plot the graph for the selected healthcare provider(s)
            fig = px.bar(
                filtered_data,
                x="healthcareprovidername",
                y="clientcount",
                color="insuranceplanlevel",
                barmode="group",
                title=f"Insurance Plan Distribution ({selected_provider})",
                labels={
                    "healthcareprovidername": "Healthcare Provider",
                    "clientcount": "Number of Clients",
                    "insuranceplanlevel": "Insurance Plan Level"
                }
            )
    
            # Update layout for better appearance
            fig.update_layout(
                height=600,
                width=1000,
                xaxis_title="Healthcare Provider",
                yaxis_title="Number of Clients",
                legend_title="Insurance Plan Level",
                title_font_size=18,
            )
            st.plotly_chart(fig, use_container_width=True)
    
        else:
            st.warning("No data found for Insurance Plan Distribution. Ensure the database is populated.")

    elif selected_query == "Revenue Contribution by Agent":
        st.subheader("Revenue Contribution by Agent")
        data = revenue_contribution_by_agent(engine)
        
        if not data.empty:
            # Ensure 'Year' column is treated as an integer
            data['year'] = data['year'].astype(int)
            
            # Format the DataFrame for display
            formatted_data = data.copy()
            formatted_data['year'] = formatted_data['year'].astype(str)  # Convert year to string to avoid commas
            st.dataframe(formatted_data)
    
            # Display a dropdown to filter data by Year
            years = sorted(data['year'].unique())
            selected_year = st.selectbox("Filter by Year", options=years)
    
            # Filter the data based on the selected year
            filtered_data = data[data['year'] == selected_year]
    
            # Plot the filtered data
            fig = px.bar(
                filtered_data,
                x="agentname",
                y="totalrevenue",
                color="totalcommission",
                title=f"Revenue Contribution by Agents for {selected_year}",
                labels={
                    "agentname": "Agent Name",
                    "totalrevenue": "Total Revenue",
                    "totalcommission": "Total Commission"
                },
                hover_data=["totalclients", "netprofit"]
            )
            st.plotly_chart(fig)
        else:
            st.warning("No data found for Revenue Contribution by Agent. Please check your database.")
    
    elif selected_query == "Medical Conditions Insights":
        st.subheader("Medical Conditions Insights")
        data = medical_conditions_insights(engine)
        st.dataframe(data)
    
        if not data.empty:
            # Ensure column names are consistent
            data.columns = [col.lower() for col in data.columns]  # Standardize to lowercase
    
            # Add a radio button for the user to select plot type
            plot_type = st.radio(
                "Select Plot Type:",
                options=["By Insurance Plan Level", "Condition Count Only"]
            )
    
            if plot_type == "By Insurance Plan Level":
                # Visualization for Medical Conditions Insights by Insurance Plan Level
                fig = px.bar(
                    data,
                    x="conditionname",  # Use the corrected lowercase column names
                    y="clientsserved",
                    color="coveragelevel",
                    barmode="group",
                    title="Medical Conditions and Associated Services by Coverage Level",
                    labels={
                        "conditionname": "Medical Condition",
                        "clientsserved": "Number of Clients",
                        "coveragelevel": "Insurance Coverage Level"
                    }
                )
                st.plotly_chart(fig)
    
            elif plot_type == "Condition Count Only":
                # Create a simpler plot for Condition and Count
                condition_count_data = data.groupby("conditionname")["conditioncount"].sum().reset_index()
    
                fig = px.bar(
                    condition_count_data,
                    x="conditionname",
                    y="conditioncount",
                    title="Top 10 Medical Conditions by Count",
                    labels={
                        "conditionname": "Medical Condition",
                        "conditioncount": "Condition Count"
                    }
                )
                st.plotly_chart(fig)
    
        else:
            st.warning("No data available for this query. Ensure the database is populated.")

    elif selected_query == "Company Profits":
        st.subheader("Company Profits Analysis")
        data = company_profits(engine)
    
        if not data.empty:
            # Display the data in a table
            st.dataframe(data)
    
            # Visualization of Revenue, Expenses, and Profits
            fig = px.bar(
                data.melt(var_name="Metric", value_name="Amount"),
                x="Metric",
                y="Amount",
                title="Company Financial Overview",
                labels={"Metric": "Financial Metric", "Amount": "Amount ($)"},
                color="Metric"
            )
            st.plotly_chart(fig)
        else:
            st.warning("No data available for this query.")
            
            
    elif selected_query == "Unused Healthcare Providers Analysis":
        st.subheader("Analysis of Unused Healthcare Providers")
        data = unused_providers_analysis(engine)
        
        # Debugging: Display dataframe to check column names
        st.dataframe(data)
        
        if not data.empty:
            # Ensure column names match exactly
            data.columns = [col.lower() for col in data.columns]  # Convert to lowercase for consistency
            
            # Visualizing unused providers
            fig = px.bar(
                data,
                x="unusedprovider",  # Use lowercase column names
                y="clientscovered",
                color="coveredplan",
                title="Unused Healthcare Providers by Covered Clients",
                labels={
                    "unusedprovider": "Healthcare Provider",
                    "clientscovered": "Number of Covered Clients",
                    "coveredplan": "Insurance Plan"
                },
                barmode="group"
            )
            fig.update_layout(
                height=600,
                width=1000,
                xaxis_title="Healthcare Providers",
                yaxis_title="Covered Clients",
                title_font_size=18
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available for this query. Ensure the database is populated.")
            
    elif selected_query == "Employee Claim Handling":
        st.subheader("Employee Claim Handling Insights")
        data = employee_claim_handling(engine)  # Replace with your query function
        st.dataframe(data)
        
        if not data.empty:
            # Visualization using a stacked bar chart
            fig = px.bar(
                data,
                x="employeename",  # Corrected column name
                y="claimcount",  # Corrected column name
                color="approvalstatus",  # Corrected column name
                title="Employee Claim Handling - Approval Status Distribution",
                labels={
                    "employeename": "Employee",
                    "claimcount": "Number of Claims",
                    "approvalstatus": "Claim Status"
                },
                barmode="stack"  # Stacked bar chart
            )
            
            # Update layout for better readability
            fig.update_layout(
                height=600,  # Adjust the height
                width=1000,  # Adjust the width
                xaxis_title="Employees",
                yaxis_title="Total Claims Processed",
                legend_title="Approval Status",
                title_font_size=18
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available for this query. Ensure the database is populated.")

    
# Run the app
if __name__ == "__main__":
    main()
