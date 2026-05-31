def _render_multi_comparison(multi_result, docs):
    """Render comparison result for 3+ documents."""
    st.divider()
    st.subheader("≡ƒôè Kß║┐t quß║ú So s├ính Nhiß╗üu Chß╗⌐ng tß╗½")

    # Pair results
    pair_results = multi_result.get('pair_results', [])

    for pair_result in pair_results:
        doc1_name = pair_result.get('doc1_name', '')
        doc2_name = pair_result.get('doc2_name', '')
        summary = pair_result.get('summary', {})
        match_rate = summary.get('match_rate', 0)

        color = "#10b981" if match_rate >= 0.8 else "#f59e0b" if match_rate >= 0.5 else "#ef4444"

        with st.expander(
            f"≡ƒôè {doc1_name} Γåö {doc2_name} ΓÇö Tß╗╖ lß╗ç khß╗¢p: {match_rate:.0%}",
            expanded=False,
        ):
            _render_comparison_result(pair_result)

    # Aggregate view
    aggregate = multi_result.get('aggregate', [])
    if aggregate:
        st.divider()
        st.subheader("≡ƒôï Tß╗òng hß╗úp tß║Ñt cß║ú chß╗⌐ng tß╗½")

        agg_data = []
        for item in aggregate:
            row = {'Tr╞░ß╗¥ng': item.get('label', '')}
            for doc in docs:
                val = item.get('values', {}).get(doc['id'], 'ΓÇö')
                row[doc['file_name'][:20]] = str(val) if val else 'ΓÇö'
            row['Tß║Ñt cß║ú khß╗¢p?'] = 'Γ£à' if item.get('all_match') else 'Γ¥î'
            agg_data.append(row)

        if agg_data:
            agg_df = pd.DataFrame(agg_data)
            
            GROUPS = {
                "≡ƒÜó Nh├│m Th├┤ng tin Vß║¡n tß║úi": ["T├áu", "Chuyß║┐n", "Cß║úng xß║┐p (POL)", "Cß║úng dß╗í (POD)", "B/L No", "Sß╗æ Vß║¡n ─æ╞ín (B/L)", "Sß╗æ container", "Sß╗æ seal", "Loß║íi container", "Ng├áy On Board"],
                "≡ƒÅó Nh├│m Th├┤ng tin ─Éß╗æi t├íc": ["Ng╞░ß╗¥i xuß║Ñt khß║⌐u", "Ng╞░ß╗¥i nhß║¡p khß║⌐u", "Shipper", "Consignee", "Notify Party", "Ng╞░ß╗¥i b├ín", "Ng╞░ß╗¥i mua", "B├¬n ─æ╞░ß╗úc th├┤ng b├ío"],
                "≡ƒôª Nh├│m Th├┤ng tin H├áng h├│a": ["M├┤ tß║ú h├áng h├│a", "Sß╗æ l╞░ß╗úng", "Trß╗ìng l╞░ß╗úng", "Trß╗ìng l╞░ß╗úng tß╗ïnh (N/W)", "Trß╗ìng l╞░ß╗úng cß║ú b├¼ (G/W)", "Thß╗â t├¡ch (CBM)", "Thß╗â t├¡ch", "Sß╗æ kiß╗çn", "M├ú HS", "─É╞ín vß╗ï", "─É╞ín gi├í", "Xuß║Ñt xß╗⌐"],
                "≡ƒÆ░ Nh├│m T├ái ch├¡nh & Hß╗úp ─æß╗ông": ["Trß╗ï gi├í", "Tß╗òng gi├í trß╗ï", "Loß║íi tiß╗ün", "─Éiß╗üu kiß╗çn giao h├áng", "─Éiß╗üu kiß╗çn c╞░ß╗¢c", "Sß╗æ Hß╗úp ─æß╗ông", "Ng├áy Hß╗úp ─æß╗ông", "Ph╞░╞íng thß╗⌐c thanh to├ín", "Tß╗òng tiß╗ün thuß║┐", "Sß╗æ Invoice", "Invoice No", "C╞░ß╗¢c ph├¡", "Sß╗æ C/O"],
                "≡ƒôà Nh├│m Th├┤ng tin Chung": ["Sß╗æ tß╗¥ khai", "Ng├áy ─æ─âng k├╜", "Ng├áy ph├ít h├ánh", "Ng├áy", "ETD", "ETA", "M├ú loß║íi h├¼nh", "C╞í quan Hß║úi quan", "Ph╞░╞íng thß╗⌐c vß║¡n chuyß╗ân", "P/L No", "Booking No"]
            }

            rendered_labels = set()
            
