import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_powershell(script, wait=True):
    """Executes a PowerShell script and returns the result."""
    try:
        # Pass script via stdin to avoid command line argument escaping issues
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "-"]

        # Use CREATE_NO_WINDOW on Windows to prevent console flashing
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags
        )

        if wait:
            stdout, stderr = process.communicate(input=script)
            return process.returncode, stdout, stderr
        else:
            process.stdin.write(script)
            process.stdin.close()
            return 0, "Running in background...", ""
    except Exception as e:
        return -1, "", str(e)


class VPNPanelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Server IKEv2 VPN 管理面板")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        if sys.platform == 'win32' and not is_admin():
            messagebox.showwarning("权限不足", "请以管理员身份运行此程序以确保能正常修改系统设置和调用PowerShell。")

        self.create_widgets()

    def create_widgets(self):
        # 创建选项卡控件
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Tab 1: 仪表盘与初始化 (Dashboard)
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text="主页 / 初始化")
        self.init_dashboard_tab()

        # Tab 2: 用户管理 (Users)
        self.tab_users = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_users, text="用户管理")
        self.init_users_tab()

        # Tab 3: 网络设置 (Network)
        self.tab_network = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_network, text="网络与IP池设置")
        self.init_network_tab()

    def log(self, message):
        self.text_log.config(state='normal')
        self.text_log.insert(tk.END, message + "\n")
        self.text_log.see(tk.END)
        self.text_log.config(state='disabled')
        self.root.update_idletasks()

    def init_dashboard_tab(self):
        frame = ttk.LabelFrame(self.tab_dashboard, text="服务状态与一键部署")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.lbl_status = ttk.Label(frame, text="VPN服务状态: 未知", font=("Arial", 12))
        self.lbl_status.pack(pady=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)

        btn_check = ttk.Button(btn_frame, text="检查状态", command=self.check_status)
        btn_check.pack(side=tk.LEFT, padx=5)

        btn_start = ttk.Button(btn_frame, text="启动服务", command=self.start_service)
        btn_start.pack(side=tk.LEFT, padx=5)

        btn_stop = ttk.Button(btn_frame, text="停止服务", command=self.stop_service)
        btn_stop.pack(side=tk.LEFT, padx=5)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)

        ttk.Label(frame, text="首次使用需初始化RRAS并申请公共域名证书 (Let's Encrypt)").pack(pady=5)

        domain_frame = ttk.Frame(frame)
        domain_frame.pack(pady=5)
        ttk.Label(domain_frame, text="绑定域名: ").pack(side=tk.LEFT)
        self.entry_domain = ttk.Entry(domain_frame, width=25)
        self.entry_domain.pack(side=tk.LEFT, padx=5)

        email_frame = ttk.Frame(frame)
        email_frame.pack(pady=5)
        ttk.Label(email_frame, text="管理员邮箱: ").pack(side=tk.LEFT)
        self.entry_email = ttk.Entry(email_frame, width=25)
        self.entry_email.pack(side=tk.LEFT, padx=5)

        btn_init = ttk.Button(frame, text="一键初始化环境并配置证书", command=self.init_env_async)
        btn_init.pack(pady=10)

        self.text_log = tk.Text(frame, height=8, state='disabled')
        self.text_log.pack(fill="both", expand=True, padx=10, pady=10)

        # Check initial status
        self.check_status()

    def check_status(self):
        self.log("正在检查服务状态...")
        script = """
        $service = Get-Service RemoteAccess -ErrorAction SilentlyContinue
        if ($service) {
            Write-Output $service.Status
        } else {
            Write-Output "NotInstalled"
        }
        """
        code, out, err = run_powershell(script)
        status_text = out.strip()
        if "Running" in status_text:
            self.lbl_status.config(text="VPN服务状态: 运行中", foreground="green")
            self.log("RemoteAccess 服务运行中。")
        elif "Stopped" in status_text:
            self.lbl_status.config(text="VPN服务状态: 已停止", foreground="red")
            self.log("RemoteAccess 服务已停止。")
        elif "NotInstalled" in status_text:
            self.lbl_status.config(text="VPN服务状态: 未安装", foreground="gray")
            self.log("RemoteAccess 角色未安装。")
        else:
            self.lbl_status.config(text="VPN服务状态: 未知", foreground="black")

    def start_service(self):
        self.log("正在启动 VPN 服务...")
        code, out, err = run_powershell("Start-Service RemoteAccess -ErrorAction Stop")
        if code == 0:
            self.log("服务已启动。")
        else:
            self.log(f"启动失败: {err}")
        self.check_status()

    def stop_service(self):
        if not messagebox.askyesno("确认", "确定要停止 VPN 服务吗？\n这将断开所有当前连接。"):
            return
        self.log("正在停止 VPN 服务...")
        code, out, err = run_powershell("Stop-Service RemoteAccess -Force -ErrorAction Stop")
        if code == 0:
            self.log("服务已停止。")
        else:
            self.log(f"停止失败: {err}")
        self.check_status()

    def init_env_async(self):
        domain = self.entry_domain.get().strip()
        email = self.entry_email.get().strip()

        if not domain or not email:
            messagebox.showerror("错误", "请输入绑定的域名和管理员邮箱！")
            return

        if not messagebox.askyesno("确认", "初始化操作将安装RRAS角色，申请Let's Encrypt证书并配置VPN及NAT。\n这可能需要几分钟时间，且期间网络可能会短暂中断。\n是否继续？"):
            return

        threading.Thread(target=self.init_env, args=(domain, email), daemon=True).start()

    def init_env(self, domain, email):
        self.log("开始初始化环境...")

        # 1. Install RRAS Role
        self.log("正在安装 Routing and Remote Access 角色...")
        install_script = "Install-WindowsFeature -Name DirectAccess-VPN, Routing -IncludeManagementTools"
        code, out, err = run_powershell(install_script)
        if code != 0:
            self.log(f"角色安装失败: {err}")
            return
        self.log("角色安装成功。")

        # 2. Configure VPN and NAT
        self.log("正在配置 VPN 和 NAT 服务...")
        config_script = """
        Install-RemoteAccess -VpnType Vpn -ErrorAction SilentlyContinue

        # Enable required authentication protocols for IKEv2 EAP-MSCHAPv2
        Set-VpnAuthProtocol -UserAuthProtocolAccepted MsChapv2, Eap -ErrorAction SilentlyContinue

        # Configure NAT on the interface that connects to internet (Assuming it's the default one, or we set to allow all)
        # Note: robust NAT setup might require specifying the external interface name.
        # For simplicity, we enable Routing and set NAT on the interface with a default gateway
        $ext_if = Get-NetIPInterface | Where-Object {$_.InterfaceAlias -notmatch "Loopback" -and $_.AddressFamily -eq "IPv4"} | Select-Object -First 1
        if ($ext_if) {
            Get-NetNat -Name "VPN-NAT" -ErrorAction SilentlyContinue | Remove-NetNat -Confirm:$false
            New-NetNat -Name "VPN-NAT" -InternalIPInterfaceAddressPrefix "10.10.10.0/24" -ErrorAction SilentlyContinue
        }
        Set-RemoteAccess -VpnType Vpn
        """
        code, out, err = run_powershell(config_script)

        # 3. Setup Posh-ACME and request cert
        self.log("正在安装 Posh-ACME 并申请 Let's Encrypt 证书...")
        cert_script = f"""
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -ErrorAction SilentlyContinue
        Install-Module -Name Posh-ACME -Force -AcceptLicense -ErrorAction SilentlyContinue
        Import-Module Posh-ACME

        Set-PAServer LE_PROD

        # Use the Standalone plugin to handle the HTTP-01 challenge by spinning up a temporary web server
        # This requires Port 80 to be open and not used by IIS or another service
        New-PACertificate {domain} -AcceptTOS -Contact {email} -Install -Plugin Standalone

        # Bind the certificate to SSTP and IKEv2
        $cert = Get-ChildItem -Path Cert:\\LocalMachine\\My | Where-Object Subject -match "{domain}" | Select-Object -First 1
        if ($cert) {{
            $hash = $cert.Thumbprint
            Write-Output "Certificate generated: $hash"

            # Bind to SSTP
            netsh http add sslcert ipport=0.0.0.0:443 certhash=$hash appid={{ba195980-ce14-46a0-8d7b-40ab898c6428}} certstorename=MY
            netsh ras set sstp-ssl-cert hash=$hash

            # Bind to IKEv2
            # First, check if RemoteAccess service is running
            if ((Get-Service RemoteAccess).Status -eq 'Running') {{
                Set-VpnAuthProtocol -CertificateThumbprint $hash -ErrorAction SilentlyContinue
                Write-Output "Bound certificate to IKEv2."
            }} else {{
                Write-Output "RemoteAccess service not running. Could not bind to IKEv2 via PowerShell, please check netsh or GUI."
            }}

            # Restart RRAS to apply changes
            Restart-Service RemoteAccess -Force -ErrorAction SilentlyContinue
        }} else {{
            Write-Error "Certificate generation failed."
        }}
        """
        code, out, err = run_powershell(cert_script)
        if "Certificate generated" in out:
            self.log(f"证书申请并配置成功！")
        else:
            self.log(f"证书配置出现问题，请检查日志。")
            if err:
                self.log(err)

        self.log("环境初始化完成。")

        # Refresh status in main thread
        self.root.after(0, self.check_status)

    def init_users_tab(self):
        # 左右分栏
        left_frame = ttk.Frame(self.tab_users)
        left_frame.pack(side=tk.LEFT, fill="y", padx=20, pady=20)

        right_frame = ttk.LabelFrame(self.tab_users, text="用户列表")
        right_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=20, pady=20)

        # 左侧输入框
        ttk.Label(left_frame, text="添加 / 修改用户").pack(pady=10)

        ttk.Label(left_frame, text="用户名:").pack(anchor='w')
        self.entry_username = ttk.Entry(left_frame)
        self.entry_username.pack(fill='x', pady=5)

        ttk.Label(left_frame, text="密码:").pack(anchor='w')
        self.entry_password = ttk.Entry(left_frame, show="*")
        self.entry_password.pack(fill='x', pady=5)

        btn_add_user = ttk.Button(left_frame, text="添加用户并允许拨入", command=self.add_user)
        btn_add_user.pack(fill='x', pady=10)

        btn_del_user = ttk.Button(left_frame, text="删除选中用户", command=self.delete_user)
        btn_del_user.pack(fill='x', pady=5)

        btn_refresh = ttk.Button(left_frame, text="刷新用户列表", command=self.refresh_users)
        btn_refresh.pack(fill='x', pady=20)

        # 右侧表格
        columns = ("username", "dial_in", "status")
        self.tree_users = ttk.Treeview(right_frame, columns=columns, show='headings')
        self.tree_users.heading("username", text="用户名")
        self.tree_users.heading("dial_in", text="允许拨入")
        self.tree_users.heading("status", text="当前在线")

        self.tree_users.column("username", width=120)
        self.tree_users.column("dial_in", width=80, anchor='center')
        self.tree_users.column("status", width=80, anchor='center')
        self.tree_users.pack(fill="both", expand=True, padx=10, pady=10)

        # Load initial users
        self.root.after(500, self.refresh_users)

    def refresh_users(self):
        # Clear existing items
        for item in self.tree_users.get_children():
            self.tree_users.delete(item)

        script = """
        $users = Get-LocalUser | Select-Object Name, Enabled
        $results = @()
        foreach ($u in $users) {
            # Get dial-in properties via ADSI
            $username = $u.Name
            try {
                $userObj = [ADSI]"WinNT://$env:COMPUTERNAME/$username,user"
                $dialIn = $userObj.msNPAllowDialin
                # $dialIn can be True, False, or null (Control Access through NPS)
                $dialInStr = if ($null -eq $dialIn) { "NPS" } elseif ($dialIn) { "Yes" } else { "No" }
            } catch {
                $dialInStr = "Error"
            }

            # Check if user is connected
            $activeConns = Get-RemoteAccessConnectionStatistics -ErrorAction SilentlyContinue
            $status = "Offline"
            if ($activeConns) {
                foreach ($conn in $activeConns) {
                    if ($conn.UserName -eq $username -or $conn.UserName -match "\\$username$") {
                        $status = "Online"
                        break
                    }
                }
            }

            $results += [PSCustomObject]@{
                Username = $username
                DialIn = $dialInStr
                Status = $status
            }
        }
        $results | ConvertTo-Json
        """
        code, out, err = run_powershell(script)
        if code == 0 and out.strip():
            import json
            try:
                users = json.loads(out)
                if not isinstance(users, list):
                    users = [users]
                for u in users:
                    self.tree_users.insert('', tk.END, values=(u.get('Username'), u.get('DialIn'), u.get('Status')))
            except json.JSONDecodeError:
                pass

    def add_user(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()
        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码！")
            return

        # Escape single quotes in username and password for PowerShell
        ps_username = username.replace("'", "''")
        ps_password = password.replace("'", "''")

        # Create or update user and set dial-in
        script = f"""
        $Password = ConvertTo-SecureString '{ps_password}' -AsPlainText -Force
        $user = Get-LocalUser -Name '{ps_username}' -ErrorAction SilentlyContinue
        if ($user) {{
            Set-LocalUser -Name '{ps_username}' -Password $Password
            Write-Output "User updated."
        }} else {{
            New-LocalUser '{ps_username}' -Password $Password -FullName '{ps_username} VPN User' -Description "Created by VPN Panel"
            Write-Output "User created."
        }}

        # Set Dial-in permission
        $userObj = [ADSI]"WinNT://$env:COMPUTERNAME/{ps_username},user"
        $userObj.Put("msNPAllowDialin", $true)
        $userObj.SetInfo()
        """
        code, out, err = run_powershell(script)
        if code == 0:
            if "updated" in out:
                messagebox.showinfo("成功", f"用户 {username} 密码已修改，并确保允许拨入。")
            else:
                messagebox.showinfo("成功", f"用户 {username} 已添加并允许拨入。")
            self.refresh_users()
        else:
            messagebox.showerror("错误", f"添加/修改用户失败: {err}")

    def delete_user(self):
        selected = self.tree_users.selection()
        if not selected:
            messagebox.showwarning("警告", "请先在列表中选中一个用户！")
            return

        item = self.tree_users.item(selected[0])
        username = item['values'][0]

        if messagebox.askyesno("确认", f"确定要删除用户 {username} 吗？"):
            script = f'Remove-LocalUser -Name "{username}"'
            code, out, err = run_powershell(script)
            if code == 0:
                self.refresh_users()
            else:
                messagebox.showerror("错误", f"删除用户失败: {err}")

    def init_network_tab(self):
        frame = ttk.LabelFrame(self.tab_network, text="VPN IP池与网络设置")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # IP 地址池设置
        pool_frame = ttk.Frame(frame)
        pool_frame.pack(pady=10)

        ttk.Label(pool_frame, text="IP池 起始地址:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_ip_start = ttk.Entry(pool_frame, width=15)
        self.entry_ip_start.insert(0, "10.10.10.10")
        self.entry_ip_start.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(pool_frame, text="IP池 结束地址:").grid(row=1, column=0, padx=5, pady=5)
        self.entry_ip_end = ttk.Entry(pool_frame, width=15)
        self.entry_ip_end.insert(0, "10.10.10.250")
        self.entry_ip_end.grid(row=1, column=1, padx=5, pady=5)

        btn_apply_pool = ttk.Button(frame, text="应用 IP 池设置", command=self.apply_ip_pool)
        btn_apply_pool.pack(pady=10)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)

        ttk.Label(frame, text="DNS 设置 (客户端拨入后获取的DNS):").pack(pady=5)
        dns_frame = ttk.Frame(frame)
        dns_frame.pack(pady=5)

        ttk.Label(dns_frame, text="主 DNS:").grid(row=0, column=0, padx=5)
        self.entry_dns1 = ttk.Entry(dns_frame, width=15)
        self.entry_dns1.insert(0, "8.8.8.8")
        self.entry_dns1.grid(row=0, column=1, padx=5)

        ttk.Label(dns_frame, text="备 DNS:").grid(row=0, column=2, padx=5)
        self.entry_dns2 = ttk.Entry(dns_frame, width=15)
        self.entry_dns2.insert(0, "1.1.1.1")
        self.entry_dns2.grid(row=0, column=3, padx=5)

        btn_apply_dns = ttk.Button(frame, text="应用 DNS 设置", command=self.apply_dns)
        btn_apply_dns.pack(pady=10)

    def apply_ip_pool(self):
        start_ip = self.entry_ip_start.get().strip()
        end_ip = self.entry_ip_end.get().strip()
        if not start_ip or not end_ip:
            messagebox.showwarning("警告", "请输入有效的IP地址范围！")
            return

        # Configure static IP pool for remote clients
        script = f"""
        # Clear existing ranges first
        netsh ras ip show range | ForEach-Object {{
            if ($_ -match "([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)\\s+-\\s+([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)") {{
                netsh ras ip delete range $($matches[1]) $($matches[2])
            }}
        }}

        netsh ras ip add range {start_ip} {end_ip}
        netsh ras ip set addrassign method=pool

        # Also need to update the NAT rule to cover the new pool
        # Assuming typical /24 subnet for the pool just as a broad stroke
        $ipParts = "{start_ip}".Split('.')
        if ($ipParts.Count -eq 4) {{
            $network = "$($ipParts[0]).$($ipParts[1]).$($ipParts[2]).0/24"
            Get-NetNat -Name "VPN-NAT" -ErrorAction SilentlyContinue | Remove-NetNat -Confirm:$false
            New-NetNat -Name "VPN-NAT" -InternalIPInterfaceAddressPrefix $network -ErrorAction SilentlyContinue
        }}
        """
        code, out, err = run_powershell(script)
        if code == 0:
            messagebox.showinfo("成功", "IP 地址池已更新。")
        else:
            messagebox.showerror("错误", f"更新 IP 地址池失败: {err}")

    def apply_dns(self):
        dns1 = self.entry_dns1.get().strip()
        dns2 = self.entry_dns2.get().strip()

        if not dns1 and not dns2:
            messagebox.showwarning("警告", "请至少输入一个DNS地址！")
            return

        # Configure DNS for remote access clients
        # For standard RRAS static pools without DHCP, we can set it via netsh and registry.
        reg_cmds = []
        if dns1:
            # Set-DnsClientServerAddress requires an interface alias, but we can set the ras interface DNS settings
            reg_cmds.append(f'Set-ItemProperty -Path "HKLM:\\System\\CurrentControlSet\\Services\\RemoteAccess\\Parameters\\IP" -Name "DNS" -Value "{dns1}"')
            reg_cmds.append(f'netsh ras ip set dnsserver "{dns1}"')

        script = "\n".join(reg_cmds)
        code, out, err = run_powershell(script)

        messagebox.showinfo("成功", "DNS设置已更新。\n(注: 某些环境下VPN客户端可能继承服务器主网卡的DNS)")

if __name__ == "__main__":
    root = tk.Tk()
    app = VPNPanelApp(root)
    root.mainloop()
