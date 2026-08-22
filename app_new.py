# IMPORTANT FIX
# உங்கள் app_new.py-ல் line 1187-ல் இருந்த தவறான Arabic comma:
# library_records[1:،]
# இப்போது சரியான English slice syntax பயன்படுத்தப்பட்டுள்ளது:
# library_records[1:]

# கீழே உள்ள code பகுதியை உங்கள் app_new.py-ல்
# Accession Management section-ல் மாற்றிப் பயன்படுத்தவும்.

elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader(
        "⚙️ 5. Accession எண்கள் மற்றும் Batch ஒதுக்கீடு மேலாண்மை"
    )

    st.info(
        "💡 சரிபார்ப்பு மற்றும் ஒத்திசைவு பணிகள் முடிந்த பிறகு "
        "இந்தப் பணியைச் செய்யவும்."
    )

    if (
        not sheet_library_details
        or not sheet_vendor_wise
        or not sheet_physically
    ):
        st.error(
            "❌ Google Sheet தரவுகள் முழுமையாகக் கிடைக்கவில்லை!"
        )
    else:
        library_records = sheet_library_details.get_all_values()
        vendor_data = sheet_vendor_wise.get_all_values()
        physical_records = sheet_physically.get_all_values()

        if len(library_records) > 1:
            central_value = (
                library_records[1][5]
                if (
                    len(library_records[1]) > 5
                    and str(library_records[1][5]).strip()
                )
                else "1001"
            )

            st.markdown("---")
            st.markdown(
                "### 🏷️ 1. Last Central Accession Number"
            )

            c1, c2 = st.columns([2, 3])
            c1.metric(
                "தற்போதைய Central Number",
                central_value,
            )

            with c2:
                new_central = st.number_input(
                    "புதிய Central Accession Number",
                    min_value=1,
                    value=(
                        int(central_value)
                        if str(central_value).isdigit()
                        else 1001
                    ),
                )

                if st.button(
                    "💾 Central Number புதுப்பி",
                    key="btn_update_central",
                ):
                    try:
                        sheet_library_details.update_cell(
                            2,
                            6,
                            new_central,
                        )
                        st.success(
                            "✅ Central Accession Number "
                            "புதுப்பிக்கப்பட்டது!"
                        )
                        st.rerun()
                    except Exception as error:
                        st.error(
                            f"❌ புதுப்பிப்பு பிழை: {error}"
                        )

            st.markdown("---")
            st.markdown(
                "### 🚀 2. Final Accession Allocation"
            )
            st.warning(
                "⚠️ இந்த செயல் Google Sheet-ல் "
                "நிரந்தரமாகத் தரவை மாற்றும்."
            )

            if st.button(
                "⚡ Final Allocation தொடங்கு",
                key="btn_final_sync",
                use_container_width=True,
            ):
                with st.spinner(
                    "⏳ Accession எண்கள் ஒதுக்கப்படுகின்றன..."
                ):
                    try:
                        current_central = (
                            int(central_value)
                            if str(central_value).isdigit()
                            else 1001
                        )

                        library_accessions = {}

                        # FIXED LINE: library_records[1:]
                        for row_index, row in enumerate(
                            library_records[1:],
                            start=2,
                        ):
                            if len(row) >= 7:
                                code = str(row[1]).strip()
                                last_accession = (
                                    int(row[6])
                                    if str(row[6]).isdigit()
                                    else 1000
                                )

                                if code:
                                    library_accessions[code] = {
                                        "last_acc": last_accession,
                                        "row_idx": row_index,
                                    }

                        vendor_updates = []
                        updated_count = 0

                        for physical in physical_records[1:]:
                            if len(physical) < 8:
                                continue

                            vendor_clean = clean_text(physical[0])
                            title_clean = clean_text(physical[1])
                            required_quantity = (
                                int(physical[6])
                                if str(physical[6]).isdigit()
                                else 0
                            )
                            matched_count = 0

                            for row_index, vendor_row in enumerate(
                                vendor_data[1:],
                                start=2,
                            ):
                                if len(vendor_row) <= 14:
                                    continue

                                row_title = clean_text(vendor_row[4])
                                row_publisher = clean_text(vendor_row[9])
                                row_vendor = clean_text(vendor_row[10])
                                library_code = str(
                                    vendor_row[14]
                                ).strip()

                                vendor_match = vendor_clean in {
                                    row_publisher,
                                    row_vendor,
                                }

                                title_match = (
                                    title_clean in row_title
                                    or row_title in title_clean
                                )

                                if vendor_match and title_match:
                                    if matched_count < required_quantity:
                                        current_central += 1

                                        if library_code in library_accessions:
                                            library_accessions[
                                                library_code
                                            ]["last_acc"] += 1
                                            library_accession = (
                                                library_accessions[
                                                    library_code
                                                ]["last_acc"]
                                            )
                                        else:
                                            library_accession = 1001

                                        vendor_updates.append({
                                            "range": (
                                                f"S{row_index}:V{row_index}"
                                            ),
                                            "values": [[
                                                1,
                                                0,
                                                current_central,
                                                library_accession,
                                            ]],
                                        })

                                        matched_count += 1
                                        updated_count += 1
                                    else:
                                        vendor_updates.append({
                                            "range": (
                                                f"S{row_index}:V{row_index}"
                                            ),
                                            "values": [[
                                                0,
                                                1,
                                                "",
                                                "",
                                            ]],
                                        })

                        if vendor_updates:
                            sheet_vendor_wise.batch_update(
                                vendor_updates
                            )

                        library_updates = [{
                            "range": "F2",
                            "values": [[current_central]],
                        }]

                        for code, item in library_accessions.items():
                            library_updates.append({
                                "range": (
                                    f"G{item['row_idx']}"
                                ),
                                "values": [[item["last_acc"]]],
                            })

                        sheet_library_details.batch_update(
                            library_updates
                        )

                        st.success(
                            f"🎉 {updated_count} புத்தகங்களுக்கு "
                            "Accession எண்கள் ஒதுக்கப்பட்டன!"
                        )
                        time.sleep(1)
                        st.rerun()

                    except Exception as error:
                        st.error(
                            f"❌ Final Allocation பிழை: {error}"
                        )

            st.markdown("---")
            st.markdown(
                "### 🏛️ 3. நூலக வாரியான Last Accession Number"
            )

            extracted = []

            # FIXED LINE: library_records[1:]
            for row_index, row in enumerate(
                library_records[1:],
                start=2,
            ):
                if len(row) >= 3:
                    code = str(row[1]).strip()
                    name = str(row[2]).strip()
                    accession = (
                        str(row[6]).strip()
                        if len(row) > 6
                        else ""
                    )

                    if code and code.lower() != "nan":
                        extracted.append({
                            "row_idx": row_index,
                            "Lib Code": code,
                            "Library Name": name,
                            "Last Accession Number": accession,
                        })

            library_df = pd.DataFrame(extracted)

            category = st.radio(
                "நூலக வகை",
                [
                    "அனைத்தும் (All 103)",
                    "DCL",
                    "FTB",
                    "BL",
                    "VL",
                ],
                horizontal=True,
            )

            filtered_df = library_df.copy()

            if category != "அனைத்தும் (All 103)":
                filtered_df = filtered_df[
                    filtered_df["Lib Code"]
                    .astype(str)
                    .str.upper()
                    .str.contains(
                        category.upper(),
                        na=False,
                    )
                ]

            st.dataframe(
                filtered_df[[
                    "Lib Code",
                    "Library Name",
                    "Last Accession Number",
                ]],
                use_container_width=True,
            )

            options = [
                f"{row['Lib Code']} - {row['Library Name']}"
                for _, row in filtered_df.iterrows()
            ]

            if options:
                selected_option = st.selectbox(
                    "நூலகத்தைத் தேர்ந்தெடுக்கவும்",
                    ["-- தேர்ந்தெடுக்கவும் --"] + options,
                )

                if selected_option != "-- தேர்ந்தெடுக்கவும் --":
                    selected_code = selected_option.split(
                        " - ",
                        1,
                    )[0].strip()

                    selected_row = filtered_df[
                        filtered_df["Lib Code"] == selected_code
                    ].iloc[0]

                    row_index = int(selected_row["row_idx"])
                    current_accession = str(
                        selected_row["Last Accession Number"]
                    ).strip()

                    current_accession = (
                        int(current_accession)
                        if current_accession.isdigit()
                        else 1000
                    )

                    new_accession = st.number_input(
                        f"{selected_code} - புதிய Accession Number",
                        min_value=1,
                        value=current_accession,
                    )

                    if st.button(
                        "💾 நூலக Accession Number புதுப்பி",
                        key="btn_update_lib",
                        use_container_width=True,
                    ):
                        try:
                            sheet_library_details.update_cell(
                                row_index,
                                7,
                                new_accession,
                            )
                            st.success(
                                "✅ நூலக Accession Number "
                                "புதுப்பிக்கப்பட்டது!"
                            )
                            st.rerun()
                        except Exception as error:
                            st.error(
                                f"❌ புதுப்பிப்பு பிழை: {error}"
                            )
            else:
                st.warning(
                    "⚠️ இந்த வகையில் நூலகங்கள் கிடைக்கவில்லை!"
                )
