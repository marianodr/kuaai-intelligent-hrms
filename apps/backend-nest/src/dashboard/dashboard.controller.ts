import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { DashboardService } from './dashboard.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@UseGuards(JwtAuthGuard)
@Controller('dashboard')
export class DashboardController {
  constructor(private readonly dashboardService: DashboardService) {}

  @Get('today')
  getTodayAttendance() {
    return this.dashboardService.getTodayAttendance();
  }

  @Get('monthly-average')
  getMonthlyAverage(
    @Query('month') month: string,
    @Query('year') year: string,
  ) {
    const now = new Date();
    return this.dashboardService.getMonthlyAverage(
      month ? +month : now.getMonth() + 1,
      year ? +year : now.getFullYear(),
    );
  }

  @Get('tardiness')
  getTardinessReport(
    @Query('month') month: string,
    @Query('year') year: string,
  ) {
    const now = new Date();
    return this.dashboardService.getTardinessReport(
      month ? +month : now.getMonth() + 1,
      year ? +year : now.getFullYear(),
    );
  }
}
