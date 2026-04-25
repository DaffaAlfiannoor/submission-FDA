"""
Olist E-Commerce Analytics Dashboard
Streamlit interactive dashboard for data analysis submission
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist E-Commerce Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(90deg, #264653, #2A9D8F);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .sub-header {font-size: 1rem; color: #6c757d; margin-bottom: 1.5rem;}
    .metric-card {
        background: white; border-radius: 12px;
        padding: 1rem 1.2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #2A9D8F;
    }
    .section-header {
        font-size: 1.3rem; font-weight: 600; color: #264653;
        border-bottom: 2px solid #2A9D8F; padding-bottom: 6px;
        margin: 1.5rem 0 1rem 0;
    }
    .insight-box {
        background: #f0f9f8; border-left: 4px solid #2A9D8F;
        padding: 0.8rem 1rem; border-radius: 0 8px 8px 0;
        margin: 0.5rem 0 1rem 0; font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

PALETTE = ['#264653','#2A9D8F','#E9C46A','#F4A261','#E76F51','#A8DADC','#457B9D','#6D6875']

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading datasets...")
def load_data():
    import os
    # Support both local and deployed paths
    base = os.path.dirname(__file__)
    def p(f): return os.path.join(base, f)

    customers   = pd.read_csv(p('E-commerce public dataset/customers_dataset.csv'))
    orders      = pd.read_csv(p('E-commerce public dataset/orders_dataset.csv'))
    order_items = pd.read_csv(p('E-commerce public dataset/order_items_dataset.csv'))
    payments    = pd.read_csv(p('E-commerce public dataset/order_payments_dataset.csv'))
    reviews     = pd.read_csv(p('E-commerce public dataset/order_reviews_dataset.csv'))
    products    = pd.read_csv(p('E-commerce public dataset/products_dataset.csv'))
    category_tr = pd.read_csv(p('E-commerce public dataset/product_category_name_translation.csv'))
    sellers     = pd.read_csv(p('E-commerce public dataset/sellers_dataset.csv'))
    geolocation = pd.read_csv(p('E-commerce public dataset/geolocation_dataset.csv'))

    # ── Clean & transform ─────────────────────────────────────────────────────
    date_cols = ['order_purchase_timestamp','order_approved_at',
                 'order_delivered_carrier_date','order_delivered_customer_date',
                 'order_estimated_delivery_date']
    for c in date_cols:
        orders[c] = pd.to_datetime(orders[c], errors='coerce')

    products = products.merge(category_tr, on='product_category_name', how='left')
    products['category_en'] = products['product_category_name_english'].fillna(
        products['product_category_name'].fillna('unknown'))

    geo_agg = (geolocation
        .groupby('geolocation_zip_code_prefix', as_index=False)
        .agg(lat=('geolocation_lat','mean'), lng=('geolocation_lng','mean'),
             city=('geolocation_city','first'), state=('geolocation_state','first')))

    delivered = orders[orders['order_status'] == 'delivered'].copy()

    pay_agg = (payments
        .groupby('order_id', as_index=False)['payment_value'].sum()
        .rename(columns={'payment_value': 'total_payment'}))

    # Revenue time series
    rev_df = (delivered[['order_id','order_purchase_timestamp']]
              .merge(pay_agg, on='order_id', how='inner'))
    rev_df['year_month'] = rev_df['order_purchase_timestamp'].dt.to_period('M')
    monthly_rev = (rev_df
        .groupby('year_month', as_index=False)
        .agg(revenue=('total_payment','sum'), orders=('order_id','count'))
        .sort_values('year_month'))
    monthly_rev['year_month_dt'] = monthly_rev['year_month'].dt.to_timestamp()
    monthly_rev['year']  = monthly_rev['year_month_dt'].dt.year
    monthly_rev['month'] = monthly_rev['year_month_dt'].dt.month

    # Category performance
    items_prod = order_items.merge(products[['product_id','category_en']], on='product_id', how='left')
    items_prod['category_en'] = items_prod['category_en'].fillna('unknown')
    items_delivered = items_prod[items_prod['order_id'].isin(delivered['order_id'])]
    cat_perf = (items_delivered
        .groupby('category_en', as_index=False)
        .agg(units_sold=('order_item_id','count'),
             total_revenue=('price','sum'), avg_price=('price','mean')))
    order_review_avg = reviews.groupby('order_id')['review_score'].mean().reset_index()
    items_review = items_delivered.merge(order_review_avg, on='order_id', how='left')
    cat_review = (items_review.groupby('category_en', as_index=False)
                  ['review_score'].mean().rename(columns={'review_score':'avg_review'}))
    cat_perf = cat_perf.merge(cat_review, on='category_en', how='left')
    cat_perf = cat_perf.sort_values('total_revenue', ascending=False)

    # State distribution
    cust_orders = (delivered[['order_id','customer_id']]
        .merge(customers[['customer_id','customer_state']], on='customer_id'))
    state_stats = (cust_orders
        .groupby('customer_state', as_index=False)
        .agg(unique_customers=('customer_id','nunique'), total_orders=('order_id','count')))
    state_rev = (cust_orders.merge(pay_agg, on='order_id')
        .groupby('customer_state', as_index=False)['total_payment'].sum()
        .rename(columns={'total_payment':'revenue'}))
    state_stats = state_stats.merge(state_rev, on='customer_state', how='left')

    # RFM
    ref_date = delivered['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
    cust_rev = (delivered[['order_id','customer_id','order_purchase_timestamp']]
        .merge(pay_agg, on='order_id'))
    rfm = (cust_rev.groupby('customer_id', as_index=False)
           .agg(last_purchase=('order_purchase_timestamp','max'),
                frequency=('order_id','count'), monetary=('total_payment','sum')))
    rfm['recency'] = (ref_date - rfm['last_purchase']).dt.days
    rfm['R'] = pd.qcut(rfm['recency'], q=5, labels=[5,4,3,2,1])
    rfm['F'] = pd.qcut(rfm['frequency'].rank(method='first'), q=5, labels=[1,2,3,4,5])
    rfm['M'] = pd.qcut(rfm['monetary'], q=5, labels=[1,2,3,4,5])

    def segment(row):
        r, f, m = int(row['R']), int(row['F']), int(row['M'])
        if r>=4 and f>=4 and m>=4: return 'Champions'
        elif r>=3 and f>=3 and m>=3: return 'Loyal Customers'
        elif r>=4 and f<=2: return 'New Customers'
        elif r>=3 and f>=2 and m>=2: return 'Potential Loyalists'
        elif r<=2 and f>=4 and m>=4: return 'At Risk'
        elif r<=2 and f<=2 and m<=2: return 'Lost'
        elif r<=2 and m>=3: return "Can't Lose Them"
        else: return 'Hibernating'

    rfm['Segment'] = rfm.apply(segment, axis=1)
    rfm['spending_tier'] = pd.cut(
        rfm['monetary'],
        bins=[0,100,500,1500,5000,rfm['monetary'].max()],
        labels=['Low','Medium','High','Premium','VIP'], include_lowest=True)

    # Payment type
    pay_type = (payments.groupby('payment_type', as_index=False)
                ['payment_value'].agg(['sum','count'])
                .rename(columns={'sum':'revenue','count':'transactions'}))

    return {
        'monthly_rev': monthly_rev,
        'cat_perf': cat_perf,
        'state_stats': state_stats,
        'rfm': rfm,
        'pay_type': pay_type,
        'reviews': reviews,
        'delivered': delivered,
        'customers': customers,
        'geo_agg': geo_agg,
        'sellers': sellers,
        'pay_agg': pay_agg,
    }

data = load_data()
monthly_rev = data['monthly_rev']
cat_perf    = data['cat_perf']
state_stats = data['state_stats']
rfm         = data['rfm']

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Olist_logo.svg/320px-Olist_logo.svg.png", width=180)
    st.markdown("---")
    st.markdown("## 📂 Navigation")
    page = st.radio("", [
        "🏠 Overview",
        "📈 Revenue Trend",
        "📦 Product Categories",
        "🌍 Geographic Analysis",
        "👥 RFM Segmentation",
    ])

    st.markdown("---")
    st.markdown("### 🗓️ Date Filter")
    min_yr = int(monthly_rev['year'].min())
    max_yr = int(monthly_rev['year'].max())
    year_range = st.slider("Year Range", min_yr, max_yr, (min_yr, max_yr))

    st.markdown("---")
    st.markdown("### 📊 Top N Categories")
    top_n = st.slider("Show top N categories", 5, 30, 15)

# Filter monthly by year
mr_filt = monthly_rev[monthly_rev['year'].between(year_range[0], year_range[1])]

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🛒 Olist E-Commerce Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Brazilian E-Commerce Public Dataset • 2016–2018 • Interactive Analysis Dashboard</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠 Overview":
    total_rev   = mr_filt['revenue'].sum()
    total_ord   = mr_filt['orders'].sum()
    avg_monthly = mr_filt['revenue'].mean()
    n_customers = rfm['customer_id'].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Revenue", f"R$ {total_rev/1e6:.2f}M")
    c2.metric("📦 Total Orders", f"{total_ord:,}")
    c3.metric("📅 Avg Monthly Revenue", f"R$ {avg_monthly/1e3:.1f}K")
    c4.metric("👥 Unique Customers", f"{n_customers:,}")

    st.markdown('<div class="section-header">Revenue & Order Volume Trend</div>', unsafe_allow_html=True)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Monthly Revenue (R$)", "Monthly Order Volume"),
                        vertical_spacing=0.1)
    fig.add_trace(go.Scatter(
        x=mr_filt['year_month_dt'], y=mr_filt['revenue'],
        fill='tozeroy', line=dict(color=PALETTE[0], width=2.5),
        fillcolor='rgba(42,157,143,0.2)', name='Revenue',
        hovertemplate='%{x|%b %Y}<br>R$ %{y:,.0f}<extra></extra>'
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=mr_filt['year_month_dt'], y=mr_filt['orders'],
        marker_color=PALETTE[2], name='Orders',
        hovertemplate='%{x|%b %Y}<br>%{y:,} orders<extra></extra>'
    ), row=2, col=1)
    fig.update_layout(height=500, showlegend=False, plot_bgcolor='#F8F9FA',
                      paper_bgcolor='white', margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Top 10 States by Orders</div>', unsafe_allow_html=True)
        top_states = state_stats.nlargest(10, 'total_orders')
        fig2 = px.bar(top_states, x='customer_state', y='total_orders',
                      color='total_orders', color_continuous_scale='teal',
                      labels={'customer_state':'State','total_orders':'Orders'})
        fig2.update_layout(showlegend=False, plot_bgcolor='#F8F9FA',
                           paper_bgcolor='white', height=350, margin=dict(t=10))
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Payment Type Distribution</div>', unsafe_allow_html=True)
        fig3 = px.pie(data['pay_type'], values='revenue', names='payment_type',
                      color_discrete_sequence=PALETTE, hole=0.4)
        fig3.update_layout(height=350, margin=dict(t=10))
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown('<div class="insight-box">💡 <b>Key Insight:</b> Revenue menunjukkan tren pertumbuhan positif dengan puncak pada November 2017 (Black Friday). São Paulo mendominasi volume order dengan lebih dari 40% transaksi.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: REVENUE TREND
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📈 Revenue Trend":
    st.markdown('<div class="section-header">📈 Monthly Revenue Deep Dive</div>', unsafe_allow_html=True)

    mr_filt2 = mr_filt.copy()
    mr_filt2['mom_growth'] = mr_filt2['revenue'].pct_change() * 100
    mr_filt2['rolling_3m'] = mr_filt2['revenue'].rolling(3).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=mr_filt2['year_month_dt'], y=mr_filt2['revenue'],
        name='Monthly Revenue', mode='lines+markers',
        line=dict(color=PALETTE[0], width=2),
        marker=dict(size=6),
        hovertemplate='%{x|%b %Y}<br>R$ %{y:,.0f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=mr_filt2['year_month_dt'], y=mr_filt2['rolling_3m'],
        name='3-Month Rolling Avg', mode='lines',
        line=dict(color=PALETTE[3], width=2.5, dash='dash'),
        hovertemplate='3M Avg: R$ %{y:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title='Monthly Revenue with 3-Month Rolling Average',
        xaxis_title='Month', yaxis_title='Revenue (R$)',
        height=420, plot_bgcolor='#F8F9FA', paper_bgcolor='white',
        hovermode='x unified', legend=dict(yanchor='top', y=0.99)
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Year-over-Year Comparison</div>', unsafe_allow_html=True)
        yoy = mr_filt2.pivot_table(index='month', columns='year', values='revenue', aggfunc='sum')
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        fig4 = go.Figure()
        for i, yr in enumerate(yoy.columns):
            fig4.add_trace(go.Bar(
                x=[months[m-1] for m in yoy.index],
                y=yoy[yr],
                name=str(yr),
                marker_color=PALETTE[i]
            ))
        fig4.update_layout(barmode='group', height=380,
                           plot_bgcolor='#F8F9FA', paper_bgcolor='white',
                           yaxis_title='Revenue (R$)', margin=dict(t=10))
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Month-over-Month Growth Rate</div>', unsafe_allow_html=True)
        mr_nona = mr_filt2.dropna(subset=['mom_growth'])
        fig5 = go.Figure(go.Bar(
            x=mr_nona['year_month_dt'],
            y=mr_nona['mom_growth'],
            marker_color=[PALETTE[1] if v >= 0 else PALETTE[4] for v in mr_nona['mom_growth']],
            hovertemplate='%{x|%b %Y}<br>%{y:.1f}%<extra></extra>'
        ))
        fig5.add_hline(y=0, line_color='black', line_width=1)
        fig5.update_layout(height=380, yaxis_title='MoM Growth (%)',
                           plot_bgcolor='#F8F9FA', paper_bgcolor='white', margin=dict(t=10))
        st.plotly_chart(fig5, use_container_width=True)

    peak_row = mr_filt2.loc[mr_filt2['revenue'].idxmax()]
    st.markdown(f'<div class="insight-box">💡 <b>Insight:</b> Puncak revenue terjadi pada <b>{peak_row["year_month_dt"].strftime("%B %Y")}</b> sebesar <b>R$ {peak_row["revenue"]:,.0f}</b>. Rata-rata pertumbuhan MoM adalah <b>{mr_filt2["mom_growth"].mean():.1f}%</b>. Lonjakan November 2017 berkaitan dengan Black Friday Brazil.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Revenue Data Table</div>', unsafe_allow_html=True)
    display_df = mr_filt2[['year_month_dt','revenue','orders','mom_growth']].copy()
    display_df.columns = ['Period','Revenue (R$)','Orders','MoM Growth (%)']
    display_df['Revenue (R$)'] = display_df['Revenue (R$)'].map('R$ {:,.0f}'.format)
    display_df['MoM Growth (%)'] = display_df['MoM Growth (%)'].map(lambda x: f'{x:.1f}%' if pd.notna(x) else '-')
    display_df['Period'] = display_df['Period'].dt.strftime('%b %Y')
    st.dataframe(display_df, use_container_width=True, height=300)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PRODUCT CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📦 Product Categories":
    st.markdown('<div class="section-header">📦 Product Category Performance</div>', unsafe_allow_html=True)

    top_cat = cat_perf.head(top_n).copy()

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(top_cat.sort_values('total_revenue'),
                     x='total_revenue', y='category_en',
                     orientation='h', color='total_revenue',
                     color_continuous_scale='teal',
                     labels={'total_revenue':'Revenue (R$)','category_en':'Category'},
                     title=f'Top {top_n} Categories by Revenue')
        fig.update_layout(height=500, plot_bgcolor='#F8F9FA', paper_bgcolor='white',
                          showlegend=False, margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(top_cat.sort_values('units_sold'),
                      x='units_sold', y='category_en',
                      orientation='h', color='units_sold',
                      color_continuous_scale='oranges',
                      labels={'units_sold':'Units Sold','category_en':'Category'},
                      title=f'Top {top_n} Categories by Units Sold')
        fig2.update_layout(height=500, plot_bgcolor='#F8F9FA', paper_bgcolor='white',
                           showlegend=False, margin=dict(t=40))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Revenue vs Review Score Bubble Chart</div>', unsafe_allow_html=True)
    fig3 = px.scatter(top_cat, x='avg_review', y='total_revenue',
                      size='units_sold', color='avg_price',
                      hover_name='category_en',
                      color_continuous_scale='viridis',
                      labels={'avg_review':'Avg Review Score',
                              'total_revenue':'Total Revenue (R$)',
                              'avg_price':'Avg Price (R$)'},
                      title='Revenue vs Review Score (bubble = units sold, color = avg price)')
    fig3.add_vline(x=top_cat['avg_review'].mean(), line_dash='dash',
                   line_color='red', annotation_text='Mean Review')
    fig3.update_layout(height=420, plot_bgcolor='#F8F9FA', paper_bgcolor='white')
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown('<div class="section-header">Category Detail Table</div>', unsafe_allow_html=True)
    display_cat = top_cat[['category_en','units_sold','total_revenue','avg_price','avg_review']].copy()
    display_cat['total_revenue'] = display_cat['total_revenue'].map('R$ {:,.0f}'.format)
    display_cat['avg_price']     = display_cat['avg_price'].map('R$ {:,.2f}'.format)
    display_cat['avg_review']    = display_cat['avg_review'].map('{:.2f} ⭐'.format)
    display_cat.columns = ['Category','Units Sold','Total Revenue','Avg Price','Avg Review']
    st.dataframe(display_cat.reset_index(drop=True), use_container_width=True)

    st.markdown('<div class="insight-box">💡 <b>Insight:</b> Kategori <b>bed_bath_table</b>, <b>health_beauty</b>, dan <b>sports_leisure</b> memimpin revenue. Perhatikan bahwa kategori dengan review tinggi tidak selalu menghasilkan revenue terbesar — ada peluang untuk meningkatkan kualitas kategori high-revenue.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: GEOGRAPHIC
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🌍 Geographic Analysis":
    st.markdown('<div class="section-header">🌍 Geographic Distribution Analysis</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.choropleth(
            state_stats,
            locations='customer_state',
            color='total_orders',
            locationmode='geojson-id',
            color_continuous_scale='teal',
            title='Order Volume by State',
            labels={'total_orders':'Total Orders','customer_state':'State'},
            hover_data={'revenue': ':,.0f', 'total_orders': ':,', 'unique_customers': ':,'}
        )
        # Use bar chart fallback (choropleth needs geojson for Brazil states)
        top_st = state_stats.nlargest(15, 'total_orders')
        fig = px.bar(top_st, x='customer_state', y='total_orders',
                     color='total_orders', color_continuous_scale='teal',
                     title='Top 15 States by Order Volume',
                     labels={'customer_state':'State','total_orders':'Orders'})
        fig.update_layout(showlegend=False, height=400,
                          plot_bgcolor='#F8F9FA', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_rev_st = state_stats.nlargest(15, 'revenue')
        fig2 = px.bar(top_rev_st, x='customer_state', y='revenue',
                      color='revenue', color_continuous_scale='oranges',
                      title='Top 15 States by Revenue',
                      labels={'customer_state':'State','revenue':'Revenue (R$)'})
        fig2.update_layout(showlegend=False, height=400,
                           plot_bgcolor='#F8F9FA', paper_bgcolor='white')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Revenue per Customer by State</div>', unsafe_allow_html=True)
    state_stats2 = state_stats.copy()
    state_stats2['rev_per_customer'] = state_stats2['revenue'] / state_stats2['unique_customers']
    fig3 = px.scatter(state_stats2, x='unique_customers', y='revenue',
                      size='total_orders', text='customer_state',
                      color='rev_per_customer', color_continuous_scale='viridis',
                      title='State: Unique Customers vs Revenue (size=orders, color=rev/customer)',
                      labels={'unique_customers':'Unique Customers',
                              'revenue':'Revenue (R$)',
                              'rev_per_customer':'Rev/Customer'})
    fig3.update_traces(textposition='top center', textfont_size=9)
    fig3.update_layout(height=480, plot_bgcolor='#F8F9FA', paper_bgcolor='white')
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown('<div class="section-header">State Summary Table</div>', unsafe_allow_html=True)
    state_display = state_stats2[['customer_state','unique_customers','total_orders','revenue','rev_per_customer']].copy()
    state_display = state_display.sort_values('revenue', ascending=False)
    state_display['revenue'] = state_display['revenue'].map('R$ {:,.0f}'.format)
    state_display['rev_per_customer'] = state_display['rev_per_customer'].map('R$ {:,.2f}'.format)
    state_display.columns = ['State','Unique Customers','Total Orders','Revenue','Rev per Customer']
    st.dataframe(state_display.reset_index(drop=True), use_container_width=True)

    st.markdown('<div class="insight-box">💡 <b>Insight:</b> <b>São Paulo (SP)</b> mendominasi pasar dengan lebih dari 40% total order. State timur laut seperti BA, PE, CE memiliki potensi pertumbuhan — perlu ekspansi seller di wilayah tersebut untuk mengurangi biaya logistik.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: RFM SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────────
elif page == "👥 RFM Segmentation":
    st.markdown('<div class="section-header">👥 RFM Customer Segmentation</div>', unsafe_allow_html=True)

    seg_summary = (rfm
        .groupby('Segment', as_index=False)
        .agg(count=('customer_id','count'),
             avg_recency=('recency','mean'),
             avg_frequency=('frequency','mean'),
             avg_monetary=('monetary','mean'),
             total_revenue=('monetary','sum'))
        .sort_values('total_revenue', ascending=False))
    seg_summary['pct_customers'] = seg_summary['count'] / seg_summary['count'].sum() * 100

    seg_colors = {
        'Champions':'#264653','Loyal Customers':'#2A9D8F','New Customers':'#E9C46A',
        'Potential Loyalists':'#F4A261','At Risk':'#E76F51',
        "Can't Lose Them":'#A8DADC','Hibernating':'#457B9D','Lost':'#6D6875'
    }
    color_map = [seg_colors.get(s,'#888') for s in seg_summary['Segment']]

    col1, col2, col3 = st.columns(3)
    col1.metric("Champions", f"{seg_summary.loc[seg_summary['Segment']=='Champions','count'].values[0] if 'Champions' in seg_summary['Segment'].values else 0:,}")
    col2.metric("Loyal Customers", f"{seg_summary.loc[seg_summary['Segment']=='Loyal Customers','count'].values[0] if 'Loyal Customers' in seg_summary['Segment'].values else 0:,}")
    col3.metric("At Risk", f"{seg_summary.loc[seg_summary['Segment']=='At Risk','count'].values[0] if 'At Risk' in seg_summary['Segment'].values else 0:,}")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(seg_summary, values='count', names='Segment',
                     color='Segment', color_discrete_map=seg_colors,
                     title='Customer Distribution by RFM Segment', hole=0.3)
        fig.update_layout(height=400, paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(seg_summary.sort_values('total_revenue'),
                      x='total_revenue', y='Segment', orientation='h',
                      color='Segment', color_discrete_map=seg_colors,
                      title='Revenue Contribution by Segment',
                      labels={'total_revenue':'Revenue (R$)'})
        fig2.update_layout(showlegend=False, height=400,
                           plot_bgcolor='#F8F9FA', paper_bgcolor='white')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">RFM Scatter: Recency vs Monetary</div>', unsafe_allow_html=True)
    rfm_sample = rfm.sample(min(5000, len(rfm)), random_state=42)
    fig3 = px.scatter(rfm_sample, x='recency', y='monetary',
                      color='Segment', color_discrete_map=seg_colors,
                      size='frequency', size_max=15,
                      opacity=0.6,
                      title='Customer Recency vs Monetary Value (size = frequency)',
                      labels={'recency':'Days Since Last Purchase','monetary':'Total Spend (R$)'})
    fig3.update_layout(height=480, plot_bgcolor='#F8F9FA', paper_bgcolor='white')
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown('<div class="section-header">Spending Tier Clustering</div>', unsafe_allow_html=True)
    tier_df = (rfm.groupby('spending_tier', observed=True, as_index=False)
               .agg(customers=('customer_id','count'),
                    avg_monetary=('monetary','mean'),
                    avg_frequency=('frequency','mean')))
    col1, col2 = st.columns(2)
    with col1:
        fig4 = px.bar(tier_df, x='spending_tier', y='customers',
                      color='spending_tier', color_discrete_sequence=PALETTE,
                      title='Customers per Spending Tier',
                      labels={'spending_tier':'Tier','customers':'Customers'})
        fig4.update_layout(showlegend=False, plot_bgcolor='#F8F9FA', paper_bgcolor='white', height=350)
        st.plotly_chart(fig4, use_container_width=True)
    with col2:
        fig5 = px.bar(tier_df, x='spending_tier', y='avg_monetary',
                      color='spending_tier', color_discrete_sequence=PALETTE,
                      title='Average Spend per Tier',
                      labels={'spending_tier':'Tier','avg_monetary':'Avg Spend (R$)'})
        fig5.update_layout(showlegend=False, plot_bgcolor='#F8F9FA', paper_bgcolor='white', height=350)
        st.plotly_chart(fig5, use_container_width=True)

    st.markdown('<div class="section-header">Segment Summary Table</div>', unsafe_allow_html=True)
    seg_display = seg_summary.copy()
    seg_display['avg_recency']  = seg_display['avg_recency'].map('{:.0f} days'.format)
    seg_display['avg_frequency'] = seg_display['avg_frequency'].map('{:.2f}'.format)
    seg_display['avg_monetary'] = seg_display['avg_monetary'].map('R$ {:,.2f}'.format)
    seg_display['total_revenue'] = seg_display['total_revenue'].map('R$ {:,.0f}'.format)
    seg_display['pct_customers'] = seg_display['pct_customers'].map('{:.1f}%'.format)
    seg_display.columns = ['Segment','Customers','Avg Recency','Avg Frequency',
                            'Avg Monetary','Total Revenue','% Customers']
    st.dataframe(seg_display.reset_index(drop=True), use_container_width=True)

    st.markdown('<div class="insight-box">💡 <b>Insight:</b> Sebagian besar pelanggan berada di segmen <b>Hibernating</b> dan <b>Lost</b> — ini umum untuk e-commerce dengan satu kali pembelian. Segmen <b>Champions</b> menghasilkan revenue jauh lebih besar secara proporsional. Fokus pada retention dan re-engagement untuk meningkatkan CLV.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#6c757d; font-size:0.85rem;'>
    🛒 Olist E-Commerce Analytics Dashboard &nbsp;|&nbsp; 
    Built with Streamlit & Plotly &nbsp;|&nbsp; 
    Dataset: Brazilian E-Commerce Public Dataset by Olist
</div>
""", unsafe_allow_html=True)
