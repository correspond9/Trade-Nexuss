<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NSE F&O Margin Strategy Builder</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f7f9fc; }
        .card { background-color: white; border-radius: 1rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
        .input-style { border: 1px solid #d1d5db; padding: 0.5rem; border-radius: 0.5rem; width: 100%; }
        .btn-primary { background-color: #4f46e5; color: white; padding: 0.75rem 1.5rem; border-radius: 0.5rem; font-weight: 600; transition: background-color 0.2s; }
        .btn-primary:hover { background-color: #4338ca; }
        .leg-row:nth-child(even) { background-color: #f3f4f6; }
        .header-bg { background-color: #eef2ff; }
        /* Custom scrollbar for mobile */
        .scroll-x { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    </style>
</head>
<body class="p-4 md:p-8">

    <div class="max-w-6xl mx-auto">
        <h1 class="text-3xl font-bold text-gray-900 mb-6 text-center">NSE F&O Margin Strategy Builder</h1>

        <!-- Strategy Configuration & Margin Display -->
        <div class="card p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4 text-indigo-700">Strategy Overview & Required Margin</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                    <label for="underlying" class="block text-sm font-medium text-gray-700">Underlying Symbol (e.g., NIFTY)</label>
                    <input type="text" id="underlying" value="NIFTY" class="input-style mt-1" oninput="calculateMargin()">
                </div>
                <div>
                    <label for="spotPrice" class="block text-sm font-medium text-gray-700">Spot Price (₹)</label>
                    <input type="number" id="spotPrice" value="20000" class="input-style mt-1" oninput="calculateMargin()">
                </div>
                <div>
                    <label for="lotSize" class="block text-sm font-medium text-gray-700">Lot Size (Units)</label>
                    <input type="number" id="lotSize" value="50" class="input-style mt-1" oninput="calculateMargin()">
                </div>
            </div>
            
            <!-- Margin Output Panel -->
            <div class="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
                <p class="text-lg font-bold text-indigo-800 flex justify-between items-center">
                    <span>Total Margin Required (Simulated)</span>
                    <span id="totalMargin" class="text-2xl">₹ 0.00</span>
                </p>
                <div id="marginBenefit" class="text-sm text-green-700 mt-1 font-medium hidden">
                    Margin Benefit Applied: <span id="benefitAmount"></span>
                </div>
                <p class="text-xs text-gray-600 mt-2">
                    Note: Margins are indicative. Real-time SPAN is dynamic and derived from exchange-published risk arrays.
                </p>
            </div>
        </div>

        <!-- Margin Simulation Parameters (For demonstration) -->
        <div class="card p-6 mb-8 bg-gray-50 border border-gray-200">
            <h3 class="text-md font-semibold mb-3 text-gray-700">Margin Simulation Parameters (Mock Risk Values)</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                    <label for="mockSpan" class="block font-medium text-gray-600">Futures/Short Option SPAN %</label>
                    <input type="number" id="mockSpan" value="15" step="0.5" class="input-style mt-1 text-xs" oninput="calculateMargin()">
                </div>
                <div>
                    <label for="mockExposure" class="block font-medium text-gray-600">Exposure/Short Margin %</label>
                    <input type="number" id="mockExposure" value="5" step="0.5" class="input-style mt-1 text-xs" oninput="calculateMargin()">
                </div>
                 <div>
                    <label for="hedgeBenefit" class="block font-medium text-gray-600">Hedge SPAN Benefit %</label>
                    <input type="number" id="hedgeBenefit" value="70" step="5" class="input-style mt-1 text-xs" oninput="calculateMargin()">
                    <p class="text-xs text-gray-500 mt-1">Reduction applied to SPAN on short leg if hedged.</p>
                </div>
            </div>
        </div>

        <!-- Strategy Builder Interface -->
        <div class="card p-6">
            <h2 class="text-xl font-semibold mb-4 text-indigo-700">Strategy Legs (Basket)</h2>
            <div id="strategyLegs" class="mb-4">
                <!-- Strategy legs will be added here -->
            </div>

            <button onclick="addLeg()" class="btn-primary w-full md:w-auto flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 mr-2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Add Option/Future Leg
            </button>
        </div>

    </div>

    <script>
        // Global state for strategy legs
        let legs = [];

        // Utility to format currency
        const formatter = new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });

        /**
         * Generates a unique ID for a strategy leg.
         * @returns {string} Unique ID.
         */
        const generateId = () => `leg-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

        /**
         * Adds a new leg to the strategy UI and state.
         */
        function addLeg() {
            const newLeg = {
                id: generateId(),
                type: 'CALL', // CALL, PUT, FUTURE
                action: 'BUY', // BUY, SELL
                strike: parseFloat(document.getElementById('spotPrice').value),
                premium: 100,
                quantity: 1,
                expiry: 'Current', // Not used in margin calculation but good practice
            };
            legs.push(newLeg);
            renderLegs();
        }

        /**
         * Removes a leg from the state and re-renders.
         * @param {string} id - The unique ID of the leg to remove.
         */
        function removeLeg(id) {
            legs = legs.filter(leg => leg.id !== id);
            renderLegs();
        }

        /**
         * Updates a property of a specific leg in the state.
         * @param {string} id - The unique ID of the leg.
         * @param {string} key - The property key to update.
         * @param {*} value - The new value.
         */
        function updateLeg(id, key, value) {
            const leg = legs.find(l => l.id === id);
            if (leg) {
                // Ensure numerical values are parsed correctly
                if (['strike', 'premium', 'quantity'].includes(key)) {
                    leg[key] = parseFloat(value);
                } else {
                    leg[key] = value;
                }
                calculateMargin();
            }
        }

        /**
         * Renders all strategy legs to the UI.
         */
        function renderLegs() {
            const container = document.getElementById('strategyLegs');
            container.innerHTML = '';
            
            legs.forEach(leg => {
                const legHtml = `
                    <div id="${leg.id}" class="leg-row card p-4 mb-3 border border-gray-200 grid grid-cols-1 md:grid-cols-8 gap-4 items-center transition-all duration-300">
                        <!-- Action -->
                        <div class="md:col-span-1">
                            <label class="block text-xs font-medium text-gray-500">Action</label>
                            <select onchange="updateLeg('${leg.id}', 'action', this.value)" class="input-style text-sm bg-white">
                                <option value="BUY" ${leg.action === 'BUY' ? 'selected' : ''} class="text-green-600">Buy</option>
                                <option value="SELL" ${leg.action === 'SELL' ? 'selected' : ''} class="text-red-600">Sell</option>
                            </select>
                        </div>
                        
                        <!-- Type -->
                        <div class="md:col-span-1">
                            <label class="block text-xs font-medium text-gray-500">Type</label>
                            <select onchange="updateLeg('${leg.id}', 'type', this.value)" class="input-style text-sm bg-white">
                                <option value="CALL" ${leg.type === 'CALL' ? 'selected' : ''}>CALL</option>
                                <option value="PUT" ${leg.type === 'PUT' ? 'selected' : ''}>PUT</option>
                                <option value="FUTURE" ${leg.type === 'FUTURE' ? 'selected' : ''}>FUTURE</option>
                            </select>
                        </div>

                        <!-- Strike Price -->
                        <div class="md:col-span-1">
                            <label class="block text-xs font-medium text-gray-500">Strike (₹)</label>
                            <input type="number" value="${leg.strike}" onchange="updateLeg('${leg.id}', 'strike', this.value)" class="input-style text-sm ${leg.type === 'FUTURE' ? 'bg-gray-200' : ''}" ${leg.type === 'FUTURE' ? 'disabled' : ''}>
                        </div>
                        
                        <!-- Premium -->
                        <div class="md:col-span-2">
                            <label class="block text-xs font-medium text-gray-500">${leg.type === 'FUTURE' ? 'Future Price (₹)' : 'Premium (₹)'}</label>
                            <input type="number" value="${leg.premium}" onchange="updateLeg('${leg.id}', 'premium', this.value)" class="input-style text-sm">
                        </div>

                        <!-- Quantity -->
                        <div class="md:col-span-1">
                            <label class="block text-xs font-medium text-gray-500">Lots</label>
                            <input type="number" value="${leg.quantity}" onchange="updateLeg('${leg.id}', 'quantity', this.value)" class="input-style text-sm" min="1">
                        </div>

                        <!-- Expiry -->
                        <div class="md:col-span-1">
                            <label class="block text-xs font-medium text-gray-500">Expiry</label>
                            <select onchange="updateLeg('${leg.id}', 'expiry', this.value)" class="input-style text-sm bg-white">
                                <option value="Current" ${leg.expiry === 'Current' ? 'selected' : ''}>Current</option>
                                <option value="Next" ${leg.expiry === 'Next' ? 'selected' : ''}>Next</option>
                            </select>
                        </div>
                        
                        <!-- Delete Button -->
                        <div class="md:col-span-1 flex justify-end items-end h-full">
                            <button onclick="removeLeg('${leg.id}')" class="text-red-500 hover:text-red-700 p-2 rounded-full transition-colors">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', legHtml);
            });

            calculateMargin();
        }

        /**
         * Calculates the total margin required for the entire strategy basket.
         * This function simulates the core logic of SPAN + Exposure with margin benefits.
         */
        function calculateMargin() {
            if (legs.length === 0) {
                document.getElementById('totalMargin').textContent = formatter.format(0);
                document.getElementById('marginBenefit').classList.add('hidden');
                return;
            }

            const spotPrice = parseFloat(document.getElementById('spotPrice').value) || 0;
            const lotSize = parseFloat(document.getElementById('lotSize').value) || 0;
            
            // Mock Risk Parameters (Simulating Exchange Data)
            const SPAN_PCT = (parseFloat(document.getElementById('mockSpan').value) || 15) / 100;
            const EXPOSURE_PCT = (parseFloat(document.getElementById('mockExposure').value) || 5) / 100;
            const HEDGE_BENEFIT_PCT = (parseFloat(document.getElementById('hedgeBenefit').value) || 70) / 100;

            let grossMargin = 0; // Margin required if all legs were naked
            let netPremiumFlow = 0; // Total premium paid/received
            let shortLegsCount = 0;
            let longLegsCount = 0;
            
            let totalShortMargin = 0;
            let isHedged = false;

            legs.forEach(leg => {
                const contractValue = (leg.type === 'FUTURE' ? leg.premium : leg.strike) * lotSize * leg.quantity;
                const premiumValue = leg.premium * lotSize * leg.quantity;

                // 1. Calculate Premium Flow (Used for net margin/P&L)
                if (leg.action === 'BUY') {
                    netPremiumFlow -= premiumValue; // Cost (Outflow)
                    longLegsCount++;
                } else {
                    netPremiumFlow += premiumValue; // Credit (Inflow)
                    shortLegsCount++;
                }

                // 2. Calculate Gross Margin (Required for short/future positions)
                if (leg.action === 'SELL' || leg.type === 'FUTURE') {
                    // Margin calculation for a naked short position (SPAN + Exposure)
                    const nakedSpan = contractValue * SPAN_PCT;
                    const exposureMargin = contractValue * EXPOSURE_PCT;
                    
                    // For a naked position, the full margin is required
                    totalShortMargin += nakedSpan + exposureMargin;
                }
            });

            // 3. Determine Net Margin (Applying Hedging Benefit)
            let finalMargin;

            // Simple logic to detect hedging: existence of at least one long and one short leg
            if (shortLegsCount > 0 && longLegsCount > 0) {
                isHedged = true;
                
                // --- Hedged Margin Simulation ---
                // In a hedged scenario (e.g., vertical spread), the risk is capped,
                // so the SPAN margin is significantly reduced by the exchange.
                
                // Calculate the theoretical gross SPAN without exposure
                const grossSpan = totalShortMargin - (lotSize * (shortLegsCount * spotPrice * EXPOSURE_PCT));
                
                // Apply the reduction percentage to the SPAN component
                const reducedSpan = grossSpan * (1 - HEDGE_BENEFIT_PCT);
                
                // Total Margin = Reduced SPAN + Full Exposure Margin on short legs
                // (Note: This is a simplification. Real SPAN is calculated on NET portfolio risk)
                finalMargin = reducedSpan + (totalShortMargin - grossSpan); // Re-adding the full Exposure part
                
                // The minimum margin required can never be less than the max theoretical loss of the spread + premium.
                // However, for this simulation, we prioritize demonstrating the SPAN benefit.
                
                finalMargin = Math.max(0, finalMargin); // Margin cannot be negative
            } else if (shortLegsCount > 0) {
                // Naked Short Position(s)
                finalMargin = totalShortMargin;
            } else if (longLegsCount > 0 && shortLegsCount === 0) {
                // Long Option Strategy (e.g., Long Call, Long Straddle)
                // Margin required is only the net premium paid (inflow is not allowed as margin)
                finalMargin = Math.abs(Math.min(0, netPremiumFlow));
            } else {
                finalMargin = 0;
            }
            
            // Adjust for total premium flow: If the net premium flow is negative (net debit),
            // the margin blocked must include the debit amount, as this is the cost paid upfront.
            const premiumDebit = Math.max(0, -netPremiumFlow);

            // Final Margin is the highest of: Calculated Risk Margin OR Premium Debit
            finalMargin = Math.max(finalMargin, premiumDebit);

            // Calculate Margin Benefit for Display
            let marginBenefitAmount = 0;
            if (isHedged) {
                const grossNakedMargin = totalShortMargin;
                marginBenefitAmount = grossNakedMargin - finalMargin;
                document.getElementById('benefitAmount').textContent = formatter.format(marginBenefitAmount);
                document.getElementById('marginBenefit').classList.remove('hidden');
            } else {
                document.getElementById('marginBenefit').classList.add('hidden');
            }

            // Update UI
            document.getElementById('totalMargin').textContent = formatter.format(finalMargin);
        }
        
        // Initial setup
        document.addEventListener('DOMContentLoaded', () => {
            // Add a starting set of legs for demonstration (e.g., a Bull Call Spread)
            legs = [
                { id: generateId(), type: 'CALL', action: 'BUY', strike: 20000, premium: 120, quantity: 1, expiry: 'Current' },
                { id: generateId(), type: 'CALL', action: 'SELL', strike: 20200, premium: 50, quantity: 1, expiry: 'Current' }
            ];
            renderLegs();
            console.log("Margin simulation initialized with mock parameters. SPAN and Exposure margins are simulated, and a 70% benefit is applied to the SPAN component of hedged strategies.");
        });

    </script>
</body>
</html>